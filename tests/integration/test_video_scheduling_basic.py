"""
Basic tests for video scheduling functionality.
"""
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.main import app
from app.models.video import Video
from app.models.ar_content import ARContent
from app.models.video_schedule import VideoSchedule
from app.core.database import AsyncSessionLocal


class TestVideoSchedulingBasic:
    """Basic tests for video scheduling."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    async def test_db_session(self):
        """Create test database session."""
        async with AsyncSessionLocal() as session:
            yield session

    @pytest.mark.asyncio
    async def test_basic_api_endpoints(self, client):
        """Test that basic endpoints are accessible."""
        # Test root endpoint
        response = client.get('/')
        assert response.status_code == 200
        
        # Test viewer endpoint with non-existent content
        response = client.get('/api/viewer/999/active-video')
        assert response.status_code == 404
        response_data = response.json()
        assert "error" in response_data
        assert "AR content not found" in response_data["error"]["message"]

    @pytest.mark.asyncio
    async def test_create_ar_content_and_video(self, test_db_session):
        """Test creating AR content and video in database."""
        import uuid
        
        # Create AR content
        ar_content = ARContent(
            company_id=1,
            project_id=1,
            unique_id=str(uuid.uuid4()),
            name="Test AR Content",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        test_db_session.add(ar_content)
        await test_db_session.commit()
        await test_db_session.refresh(ar_content)
        
        # Create video
        video = Video(
            ar_content_id=ar_content.id,
            title="Test Video",
            video_path="/tmp/test_video.mp4",
            video_url="/storage/test_video.mp4",
            duration=120.0,
            width=1920,
            height=1080,
            size_bytes=1000000,
            mime_type="video/mp4",
            status="active",
            is_active=True,
            rotation_type="none",
            rotation_order=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        test_db_session.add(video)
        await test_db_session.commit()
        await test_db_session.refresh(video)
        
        # Verify creation
        assert video.id is not None
        assert ar_content.id is not None
        
        # Set active video in AR content
        ar_content.active_video_id = video.id
        await test_db_session.commit()
        
        # Verify relationship
        await test_db_session.refresh(ar_content)
        assert ar_content.active_video_id == video.id

    @pytest.mark.asyncio
    async def test_video_schedule_creation(self, test_db_session):
        """Test creating video schedule."""
        import uuid
        
        # Create test data
        ar_content = ARContent(
            company_id=1,
            project_id=1,
            unique_id=str(uuid.uuid4()),
            name="Test AR Content",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        test_db_session.add(ar_content)
        await test_db_session.commit()
        await test_db_session.refresh(ar_content)
        
        video = Video(
            ar_content_id=ar_content.id,
            title="Test Video",
            video_path="/tmp/test_video.mp4",
            video_url="/storage/test_video.mp4",
            duration=120.0,
            width=1920,
            height=1080,
            size_bytes=1000000,
            mime_type="video/mp4",
            status="active",
            is_active=True,
            rotation_type="none",
            rotation_order=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        test_db_session.add(video)
        await test_db_session.commit()
        await test_db_session.refresh(video)
        
        # Create schedule
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(hours=2)
        
        schedule = VideoSchedule(
            video_id=video.id,
            start_time=start_time,
            end_time=end_time,
            description="Test schedule",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        test_db_session.add(schedule)
        await test_db_session.commit()
        await test_db_session.refresh(schedule)
        
        # Verify creation
        assert schedule.id is not None
        assert schedule.video_id == video.id
        assert schedule.start_time == start_time
        assert schedule.end_time == end_time

    @pytest.mark.asyncio
    async def test_viewer_endpoint_with_data(self, client, test_db_session):
        """Test viewer endpoint with actual data."""
        import uuid
        
        # Create test data
        ar_content = ARContent(
            company_id=1,
            project_id=1,
            unique_id=str(uuid.uuid4()),
            name="Test AR Content",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        test_db_session.add(ar_content)
        await test_db_session.commit()
        await test_db_session.refresh(ar_content)
        
        video = Video(
            ar_content_id=ar_content.id,
            title="Test Video",
            video_path="/tmp/test_video.mp4",
            video_url="/storage/test_video.mp4",
            duration=120.0,
            width=1920,
            height=1080,
            size_bytes=1000000,
            mime_type="video/mp4",
            status="active",
            is_active=True,
            rotation_type="none",
            rotation_order=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        test_db_session.add(video)
        await test_db_session.commit()
        await test_db_session.refresh(video)
        
        # Set active video in AR content
        ar_content.active_video_id = video.id
        await test_db_session.commit()
        
        # Test viewer endpoint
        response = client.get(f'/api/viewer/{ar_content.id}/active-video')
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == video.id
        assert data["title"] == "Test Video"
        assert data["selection_source"] == "active_default"
        assert data["video_url"] == "/storage/test_video.mp4"

    @pytest.mark.asyncio
    async def test_video_status_computation(self, test_db_session):
        """Test video status computation."""
        import uuid
        from app.services.video_scheduler import compute_video_status, compute_days_remaining
        
        # Create test data
        ar_content = ARContent(
            company_id=1,
            project_id=1,
            unique_id=str(uuid.uuid4()),
            name="Test AR Content",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        test_db_session.add(ar_content)
        await test_db_session.commit()
        await test_db_session.refresh(ar_content)
        
        # Test active video (no subscription)
        video_active = Video(
            ar_content_id=ar_content.id,
            title="Active Video",
            video_path="/tmp/active.mp4",
            video_url="/storage/active.mp4",
            is_active=True,
            rotation_type="none",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Test expired video
        video_expired = Video(
            ar_content_id=ar_content.id,
            title="Expired Video",
            video_path="/tmp/expired.mp4",
            video_url="/storage/expired.mp4",
            is_active=True,
            subscription_end=datetime.utcnow() - timedelta(days=1),
            rotation_type="none",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Test expiring video
        video_expiring = Video(
            ar_content_id=ar_content.id,
            title="Expiring Video",
            video_path="/tmp/expiring.mp4",
            video_url="/storage/expiring.mp4",
            is_active=True,
            subscription_end=datetime.utcnow() + timedelta(days=3),
            rotation_type="none",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        test_db_session.add_all([video_active, video_expired, video_expiring])
        await test_db_session.commit()
        
        # Test status computation
        assert compute_video_status(video_active) == "active"
        assert compute_video_status(video_expired) == "expired"
        assert compute_video_status(video_expiring) == "expiring"
        
        # Test days remaining computation
        assert compute_days_remaining(video_active) is None
        assert compute_days_remaining(video_expired) == 0
        assert compute_days_remaining(video_expiring) == 3


if __name__ == "__main__":
    pytest.main([__file__])