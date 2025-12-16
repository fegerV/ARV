"""
Integration tests for video scheduling and rotation functionality.
"""
import pytest
import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.main import app
from app.models.video import Video
from app.models.ar_content import ARContent
from app.models.video_schedule import VideoSchedule
from app.core.database import AsyncSessionLocal


class TestVideoSchedulingIntegration:
    """Integration tests for video scheduling and rotation."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    async def test_db_session(self):
        """Create test database session."""
        async with AsyncSessionLocal() as session:
            yield session

    @pytest.fixture
    async def sample_ar_content(self, test_db_session):
        """Create sample AR content for testing."""
        import uuid
        
        ar_content = ARContent(
            company_id=1,
            project_id=1,
            unique_id=uuid.uuid4(),
            name="Test AR Content",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        test_db_session.add(ar_content)
        await test_db_session.commit()
        await test_db_session.refresh(ar_content)
        
        return ar_content

    @pytest.fixture
    async def sample_videos(self, sample_ar_content, test_db_session):
        """Create sample videos for testing."""
        now = datetime.utcnow()
        
        videos = []
        for i in range(3):
            video = Video(
                ar_content_id=sample_ar_content.id,
                title=f"Test Video {i+1}",
                video_path=f"/tmp/test_video_{i+1}.mp4",
                video_url=f"/storage/test_video_{i+1}.mp4",
                duration=120.0,
                width=1920,
                height=1080,
                size_bytes=1000000,
                mime_type="video/mp4",
                status="active",
                is_active=(i == 0),  # First video is active
                rotation_type="none",
                rotation_order=i,
                created_at=now,
                updated_at=now
            )
            videos.append(video)
            test_db_session.add(video)
        
        await test_db_session.commit()
        for video in videos:
            await test_db_session.refresh(video)
        
        # Set active video in AR content
        sample_ar_content.active_video_id = videos[0].id
        await test_db_session.commit()
        
        return videos

    @pytest.mark.asyncio
    async def test_set_active_video_atomic(self, client, sample_ar_content, sample_videos):
        """Test that setting active video is atomic and clears other videos."""
        # Set second video as active
        response = client.patch(
            f"/api/ar-content/{sample_ar_content.id}/videos/{sample_videos[1].id}/set-active"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["active_video_id"] == sample_videos[1].id
        
        # Verify database state
        async with AsyncSessionLocal() as db:
            # Check that only second video is active
            stmt = select(Video).where(Video.ar_content_id == sample_ar_content.id)
            result = await db.execute(stmt)
            videos = result.scalars().all()
            
            active_videos = [v for v in videos if v.is_active]
            assert len(active_videos) == 1
            assert active_videos[0].id == sample_videos[1].id
            
            # Check AR content updated
            await db.refresh(sample_ar_content)
            assert sample_ar_content.active_video_id == sample_videos[1].id
            assert sample_ar_content.rotation_state == 0

    @pytest.mark.asyncio
    async def test_subscription_preset_update(self, client, sample_ar_content, sample_videos):
        """Test subscription update with presets."""
        # Test '1y' preset
        response = client.patch(
            f"/api/ar-content/{sample_ar_content.id}/videos/{sample_videos[0].id}/subscription",
            json={"subscription": "1y"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "updated"
        
        # Verify subscription is ~1 year from now
        subscription_end = datetime.fromisoformat(data["subscription_end"])
        expected_end = datetime.utcnow() + timedelta(days=365)
        assert abs((subscription_end - expected_end).total_seconds()) < 3600  # Within 1 hour
        
        # Test '2y' preset
        response = client.patch(
            f"/api/ar-content/{sample_ar_content.id}/videos/{sample_videos[0].id}/subscription",
            json={"subscription": "2y"}
        )
        
        assert response.status_code == 200
        data = response.json()
        subscription_end = datetime.fromisoformat(data["subscription_end"])
        expected_end = datetime.utcnow() + timedelta(days=730)
        assert abs((subscription_end - expected_end).total_seconds()) < 3600

    @pytest.mark.asyncio
    async def test_subscription_custom_date_update(self, client, sample_ar_content, sample_videos):
        """Test subscription update with custom ISO date."""
        future_date = (datetime.utcnow() + timedelta(days=90)).isoformat()
        
        response = client.patch(
            f"/api/ar-content/{sample_ar_content.id}/videos/{sample_videos[0].id}/subscription",
            json={"subscription": future_date}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "updated"
        
        subscription_end = datetime.fromisoformat(data["subscription_end"])
        expected_end = datetime.fromisoformat(future_date)
        assert subscription_end == expected_end

    @pytest.mark.asyncio
    async def test_subscription_past_date_deactivates_video(self, client, sample_ar_content, sample_videos):
        """Test that past subscription date deactivates video."""
        past_date = (datetime.utcnow() - timedelta(days=1)).isoformat()
        
        response = client.patch(
            f"/api/ar-content/{sample_ar_content.id}/videos/{sample_videos[0].id}/subscription",
            json={"subscription": past_date}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "updated"
        assert data["is_active"] is False
        
        # Verify AR content active_video_id is cleared if this was the active video
        async with AsyncSessionLocal() as db:
            await db.refresh(sample_ar_content)
            assert sample_ar_content.active_video_id is None

    @pytest.mark.asyncio
    async def test_rotation_type_validation(self, client, sample_ar_content, sample_videos):
        """Test rotation type validation."""
        # Test valid rotation types
        for rotation_type in ["none", "sequential", "cyclic"]:
            response = client.patch(
                f"/api/ar-content/{sample_ar_content.id}/videos/{sample_videos[0].id}/rotation",
                json={"rotation_type": rotation_type}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["rotation_type"] == rotation_type
        
        # Test invalid rotation type
        response = client.patch(
            f"/api/ar-content/{sample_ar_content.id}/videos/{sample_videos[0].id}/rotation",
            json={"rotation_type": "invalid"}
        )
        assert response.status_code == 400
        assert "Invalid rotation type" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_rotation_state_reset(self, client, sample_ar_content, sample_videos):
        """Test that rotation state resets when rotation type changes."""
        # Set initial rotation state
        async with AsyncSessionLocal() as db:
            sample_ar_content.rotation_state = 5
            await db.commit()
        
        # Change rotation type
        response = client.patch(
            f"/api/ar-content/{sample_ar_content.id}/videos/{sample_videos[0].id}/rotation",
            json={"rotation_type": "sequential"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["rotation_state"] == 0

    @pytest.mark.asyncio
    async def test_schedule_crud_operations(self, client, sample_ar_content, sample_videos):
        """Test schedule CRUD operations."""
        video = sample_videos[0]
        
        # Create schedule
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(hours=2)
        
        create_response = client.post(
            f"/api/ar-content/{sample_ar_content.id}/videos/{video.id}/schedules",
            json={
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "description": "Test schedule"
            }
        )
        
        assert create_response.status_code == 200
        schedule_data = create_response.json()
        schedule_id = schedule_data["id"]
        
        # List schedules
        list_response = client.get(
            f"/api/ar-content/{sample_ar_content.id}/videos/{video.id}/schedules"
        )
        assert list_response.status_code == 200
        schedules = list_response.json()
        assert len(schedules) == 1
        assert schedules[0]["id"] == schedule_id
        
        # Update schedule
        new_end_time = end_time + timedelta(hours=1)
        update_response = client.patch(
            f"/api/ar-content/{sample_ar_content.id}/videos/{video.id}/schedules/{schedule_id}",
            json={
                "end_time": new_end_time.isoformat(),
                "description": "Updated schedule"
            }
        )
        
        assert update_response.status_code == 200
        updated_schedule = update_response.json()
        assert updated_schedule["description"] == "Updated schedule"
        
        # Delete schedule
        delete_response = client.delete(
            f"/api/ar-content/{sample_ar_content.id}/videos/{video.id}/schedules/{schedule_id}"
        )
        assert delete_response.status_code == 200
        
        # Verify deletion
        list_response = client.get(
            f"/api/ar-content/{sample_ar_content.id}/videos/{video.id}/schedules"
        )
        assert list_response.status_code == 200
        schedules = list_response.json()
        assert len(schedules) == 0

    @pytest.mark.asyncio
    async def test_schedule_overlap_validation(self, client, sample_ar_content, sample_videos):
        """Test that overlapping schedules are rejected."""
        video = sample_videos[0]
        
        # Create first schedule
        start_time1 = datetime.utcnow()
        end_time1 = start_time1 + timedelta(hours=2)
        
        client.post(
            f"/api/ar-content/{sample_ar_content.id}/videos/{video.id}/schedules",
            json={
                "start_time": start_time1.isoformat(),
                "end_time": end_time1.isoformat(),
                "description": "First schedule"
            }
        )
        
        # Try to create overlapping schedule
        start_time2 = start_time1 + timedelta(hours=1)  # Overlaps with first
        end_time2 = start_time2 + timedelta(hours=2)
        
        response = client.post(
            f"/api/ar-content/{sample_ar_content.id}/videos/{video.id}/schedules",
            json={
                "start_time": start_time2.isoformat(),
                "end_time": end_time2.isoformat(),
                "description": "Overlapping schedule"
            }
        )
        
        assert response.status_code == 400
        assert "overlaps" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_schedule_time_validation(self, client, sample_ar_content, sample_videos):
        """Test that invalid time ranges are rejected."""
        video = sample_videos[0]
        
        # Try to create schedule with end before start
        start_time = datetime.utcnow()
        end_time = start_time - timedelta(hours=1)  # End before start
        
        response = client.post(
            f"/api/ar-content/{sample_ar_content.id}/videos/{video.id}/schedules",
            json={
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "description": "Invalid time range"
            }
        )
        
        assert response.status_code == 400
        assert "Start time must be before end time" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_enhanced_videos_list(self, client, sample_ar_content, sample_videos):
        """Test enhanced videos list with computed fields."""
        # Add subscription to first video
        async with AsyncSessionLocal() as db:
            sample_videos[0].subscription_end = datetime.utcnow() + timedelta(days=30)
            await db.commit()
        
        response = client.get(
            f"/api/ar-content/{sample_ar_content.id}/videos"
        )
        
        assert response.status_code == 200
        videos_data = response.json()
        assert len(videos_data) == 3
        
        # Check first video with subscription
        video_0 = videos_data[0]
        assert video_0["status"] == "active"
        assert video_0["days_remaining"] == 30
        assert video_0["schedules_count"] == 0
        
        # Check that computed fields are present
        for video_data in videos_data:
            assert "status" in video_data
            assert "days_remaining" in video_data
            assert "schedules_count" in video_data
            assert "schedules_summary" in video_data

    @pytest.mark.asyncio
    async def test_viewer_active_video_selection_schedule_priority(self, client, sample_ar_content, sample_videos):
        """Test viewer endpoint prioritizes scheduled videos."""
        # Create active schedule for second video
        video = sample_videos[1]
        start_time = datetime.utcnow() - timedelta(minutes=30)
        end_time = datetime.utcnow() + timedelta(minutes=30)
        
        client.post(
            f"/api/ar-content/{sample_ar_content.id}/videos/{video.id}/schedules",
            json={
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "description": "Active schedule"
            }
        )
        
        # Get active video through viewer endpoint
        response = client.get(f"/api/viewer/{sample_ar_content.id}/active-video")
        
        assert response.status_code == 200
        video_data = response.json()
        assert video_data["id"] == video.id
        assert video_data["selection_source"] == "schedule"
        assert video_data["schedule_id"] is not None

    @pytest.mark.asyncio
    async def test_viewer_no_playable_videos(self, client, sample_ar_content, sample_videos):
        """Test viewer endpoint when no videos are playable."""
        # Deactivate all videos and set past subscriptions
        async with AsyncSessionLocal() as db:
            for video in sample_videos:
                video.is_active = False
                video.subscription_end = datetime.utcnow() - timedelta(days=1)
            await db.commit()
        
        # Clear active video
        async with AsyncSessionLocal() as db:
            sample_ar_content.active_video_id = None
            await db.commit()
        
        response = client.get(f"/api/viewer/{sample_ar_content.id}/active-video")
        
        assert response.status_code == 404
        assert "No playable videos" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_viewer_subscription_expiration(self, client, sample_ar_content, sample_videos):
        """Test viewer endpoint respects subscription expiration."""
        # Set expired subscription on active video
        async with AsyncSessionLocal() as db:
            sample_videos[0].subscription_end = datetime.utcnow() - timedelta(days=1)
            await db.commit()
        
        response = client.get(f"/api/viewer/{sample_ar_content.id}/active-video")
        
        # Should return a different video or 404 if all expired
        if response.status_code == 200:
            video_data = response.json()
            assert video_data["id"] != sample_videos[0].id
            assert video_data["expires_in_days"] == 0 or video_data["expires_in_days"] is None

    @pytest.mark.asyncio
    async def test_one_and_only_one_active_video_constraint(self, client, sample_ar_content, sample_videos):
        """Test that only one video can be active at a time."""
        # Manually set multiple videos as active in database (simulating race condition)
        async with AsyncSessionLocal() as db:
            for video in sample_videos:
                video.is_active = True
            await db.commit()
        
        # Set first video as active through API
        response = client.patch(
            f"/api/ar-content/{sample_ar_content.id}/videos/{sample_videos[0].id}/set-active"
        )
        
        assert response.status_code == 200
        
        # Verify only one video is active
        async with AsyncSessionLocal() as db:
            stmt = select(Video).where(Video.ar_content_id == sample_ar_content.id)
            result = await db.execute(stmt)
            videos = result.scalars().all()
            
            active_videos = [v for v in videos if v.is_active]
            assert len(active_videos) == 1
            assert active_videos[0].id == sample_videos[0].id


if __name__ == "__main__":
    pytest.main([__file__])