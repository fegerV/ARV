"""
Integration tests for video upload functionality.
"""
import os
import pytest
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import uuid
from fastapi.testclient import TestClient
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.main import app
from app.models.video import Video
from app.models.ar_content import ARContent
from app.core.database import get_db


class TestVideoUploadIntegration:
    """Integration tests for video upload functionality."""

    @pytest.mark.asyncio
    async def test_upload_video_generates_thumbnail_and_updates_db(self, async_client, db, ar_content_factory):
        ar_content = await ar_content_factory(db)

        fake_video_bytes = b"fake video content for testing"

        async def _mock_generate_video_thumbnail(self, video_path: str, output_dir=None, thumbnail_name=None, **kwargs):
            from pathlib import Path

            media_root = os.environ["MEDIA_ROOT"]
            out_dir = Path(media_root) / "thumbnails"
            out_dir.mkdir(parents=True, exist_ok=True)

            name = thumbnail_name or "thumb.jpg"
            out_path = out_dir / name
            out_path.write_bytes(b"fake jpeg")

            return {
                "status": "ready",
                "thumbnail_path": str(out_path),
                "thumbnail_url": f"/storage/thumbnails/{out_path.name}",
            }

        with patch(
            "app.api.routes.videos.get_video_metadata",
            new=AsyncMock(
                return_value={
                    "duration": 12.0,
                    "width": 1920,
                    "height": 1080,
                    "size_bytes": len(fake_video_bytes),
                    "mime_type": "video/mp4",
                }
            ),
        ):
            with patch(
                "app.api.routes.videos.ThumbnailService.generate_video_thumbnail",
                new=_mock_generate_video_thumbnail,
            ):
                files = {
                    "videos": ("test_video.mp4", fake_video_bytes, "video/mp4"),
                }
                resp = await async_client.post(f"/api/ar-content/{ar_content.id}/videos", files=files)
                assert resp.status_code == 200

        video_id = uuid.UUID(resp.json()["videos"][0]["id"])
        v = await db.get(Video, video_id)
        assert v is not None
        assert v.thumbnail_url is not None
        assert v.thumbnail_url.startswith("/storage/thumbnails/")
        assert v.status == "ready"

        thumb_name = v.thumbnail_url.split("/")[-1]
        thumb_path = Path(os.environ["MEDIA_ROOT"]) / "thumbnails" / thumb_name
        assert thumb_path.exists()

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
        from datetime import datetime
        
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
        
        return ar_content

    def create_test_video_file(self, filename="test_video.mp4", content_type="video/mp4"):
        """Create a test video file for upload."""
        # Create a temporary file with video-like content
        temp_file = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        temp_file.write(b"fake video content for testing")
        temp_file.close()
        
        return temp_file.name

    @pytest.mark.asyncio
    async def test_complete_video_upload_flow(self, client, sample_ar_content):
        """Test complete video upload flow with preview generation."""
        # Create test video file
        video_file_path = self.create_test_video_file()
        
        try:
            # Mock the utility functions to avoid actual ffprobe calls
            with patch('app.api.routes.videos.get_video_metadata') as mock_metadata:
                mock_metadata.return_value = {
                    "duration": 120.0,
                    "width": 1920,
                    "height": 1080,
                    "size_bytes": len(b"fake video content for testing"),
                    "mime_type": "video/mp4",
                    "codec": "h264",
                    "fps": 30,
                    "bit_rate": 2500000
                }
                
                with patch('app.api.routes.videos.generate_video_thumbnail') as mock_task:
                    mock_task.delay.return_value = None
                    
                    # Upload video via API
                    with open(video_file_path, "rb") as video_file:
                        response = client.post(
                            f"/api/ar-content/{sample_ar_content.id}/videos",
                            files={"videos": ("test_video.mp4", video_file, "video/mp4")}
                        )
                    
                    assert response.status_code == 200
                    data = response.json()
                    
                    # Verify response structure
                    assert "message" in data
                    assert "videos" in data
                    assert "ar_content" in data
                    assert len(data["videos"]) == 1
                    
                    video_data = data["videos"][0]
                    
                    # Verify video metadata
                    assert video_data["title"] == "test_video.mp4"
                    assert video_data["duration"] == 120.0
                    assert video_data["width"] == 1920
                    assert video_data["height"] == 1080
                    assert video_data["status"] == "processing"
                    assert video_data["rotation_type"] == "none"
                    assert video_data["is_active"] is True  # First video should be active
                    
                    # Verify AR content was updated
                    assert data["ar_content"]["active_video_id"] == video_data["id"]
                    
                    # Verify preview task was enqueued
                    mock_task.delay.assert_called_once_with(video_data["id"])
                    
        finally:
            # Clean up temp file
            Path(video_file_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_multiple_video_upload(self, client, sample_ar_content):
        """Test uploading multiple videos at once."""
        # Create test video files
        video_file_path1 = self.create_test_video_file("test1.mp4")
        video_file_path2 = self.create_test_video_file("test2.mp4")
        
        try:
            with patch('app.api.routes.videos.get_video_metadata') as mock_metadata:
                mock_metadata.return_value = {
                    "duration": 60.0,
                    "width": 1280,
                    "height": 720,
                    "size_bytes": 1000,
                    "mime_type": "video/mp4",
                    "codec": "h264",
                    "fps": 30,
                    "bit_rate": 1500000
                }
                
                with patch('app.api.routes.videos.generate_video_thumbnail') as mock_task:
                    mock_task.delay.return_value = None
                    
                    # Upload multiple videos
                    with open(video_file_path1, "rb") as video_file1, \
                         open(video_file_path2, "rb") as video_file2:
                        
                        response = client.post(
                            f"/api/ar-content/{sample_ar_content.id}/videos",
                            files=[
                                ("videos", ("test1.mp4", video_file1, "video/mp4")),
                                ("videos", ("test2.mp4", video_file2, "video/mp4"))
                            ]
                        )
                    
                    assert response.status_code == 200
                    data = response.json()
                    
                    # Verify response structure
                    assert len(data["videos"]) == 2
                    
                    # First video should be active, second should not
                    video1_active = data["videos"][0]["is_active"]
                    video2_active = data["videos"][1]["is_active"]
                    
                    assert video1_active is True or video2_active is True
                    assert not (video1_active and video2_active)  # Only one should be active
                    
                    # Verify preview tasks were enqueued for both videos
                    assert mock_task.delay.call_count == 2
                    
        finally:
            # Clean up temp files
            Path(video_file_path1).unlink(missing_ok=True)
            Path(video_file_path2).unlink(missing_ok=True)

    def test_upload_invalid_file_type(self, client, sample_ar_content):
        """Test uploading invalid file type."""
        # Create a text file
        temp_file = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
        temp_file.write(b"This is not a video file")
        temp_file.close()
        
        try:
            with open(temp_file.name, "rb") as text_file:
                response = client.post(
                    f"/api/ar-content/{sample_ar_content.id}/videos",
                    files={"videos": ("test.txt", text_file, "text/plain")}
                )
            
            assert response.status_code == 400
            assert "Unsupported MIME type" in response.json()["detail"]
            
        finally:
            Path(temp_file.name).unlink(missing_ok=True)

    def test_upload_nonexistent_ar_content(self, client):
        """Test uploading video to non-existent AR content."""
        video_file_path = self.create_test_video_file()
        
        try:
            with open(video_file_path, "rb") as video_file:
                response = client.post(
                    "/api/ar-content/999/videos",
                    files={"videos": ("test.mp4", video_file, "video/mp4")}
                )
            
            assert response.status_code == 404
            assert "AR content not found" in response.json()["detail"]
            
        finally:
            Path(video_file_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_preview_generation_task_flow(self, test_db_session):
        """Test complete preview generation flow."""
        import uuid
        from datetime import datetime
        
        # Create test data
        ar_content = ARContent(
            company_id=1,
            project_id=1,
            unique_id=str(uuid.uuid4()),
            name="Test AR Content",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        video = Video(
            ar_content_id=ar_content.id,
            title="test_video.mp4",
            video_path="/tmp/test_video.mp4",
            video_url="/storage/test_video.mp4",
            status="processing",
            rotation_type="none",
            is_active=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        test_db_session.add(ar_content)
        test_db_session.add(video)
        await test_db_session.commit()
        await test_db_session.refresh(video)
        
        # Mock the dependencies
        with patch('app.tasks.preview_tasks.Path.exists', return_value=True):
            with patch('app.tasks.preview_tasks.build_ar_content_storage_path', return_value=Path("/tmp/storage")):
                with patch('app.tasks.preview_tasks.get_video_middle_frame_time', return_value=60.0):
                    with patch('app.tasks.preview_tasks.thumbnail_service.generate_video_thumbnail') as mock_thumbnail:
                        mock_thumbnail.return_value = {
                            "status": "ready",
                            "thumbnail_url": "/storage/previews/video_123_preview.jpg"
                        }
                        
                        with patch('app.tasks.preview_tasks.AsyncSessionLocal') as mock_session:
                            mock_db = AsyncMock()
                            mock_db.get = AsyncMock(side_effect=[video, ar_content, Mock()])
                            mock_db.commit = AsyncMock()
                            mock_session.return_value.__aenter__.return_value = mock_db
                            
                            # Run the task
                            from app.tasks.preview_tasks import generate_video_thumbnail
                            
                            result = generate_video_thumbnail(video.id)
                            
                            # Verify the thumbnail service was called with correct parameters
                            mock_thumbnail.assert_called_once_with(
                                video_path=video.video_path,
                                output_dir="/tmp/storage/previews",
                                thumbnail_name=f"video_{video.id}_preview.jpg",
                                time_position=60.0,
                                provider=None,
                                company_id=ar_content.company_id
                            )


if __name__ == "__main__":
    pytest.main([__file__])