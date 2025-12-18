"""
Unit tests for video upload functionality.
"""
import pytest
import json
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.video_utils import (
    validate_video_file,
    get_video_metadata,
    save_uploaded_video,
    generate_video_filename,
    get_video_middle_frame_time,
    ALLOWED_VIDEO_MIME_TYPES,
    ALLOWED_VIDEO_EXTENSIONS,
)
from app.api.routes.videos import upload_videos
from app.models.video import Video
from app.models.ar_content import ARContent
from app.models.company import Company
from app.tasks.preview_tasks import generate_video_thumbnail


class TestVideoUtils:
    """Test video utility functions."""

    def test_validate_video_file_success(self):
        """Test successful video file validation."""
        upload_file = Mock(spec=UploadFile)
        upload_file.content_type = "video/mp4"
        upload_file.filename = "test_video.mp4"
        
        # Should not raise exception
        validate_video_file(upload_file)

    def test_validate_video_file_invalid_mime_type(self):
        """Test validation failure with invalid MIME type."""
        upload_file = Mock(spec=UploadFile)
        upload_file.content_type = "image/jpeg"
        upload_file.filename = "test.jpg"
        
        with pytest.raises(HTTPException) as exc_info:
            validate_video_file(upload_file)
        
        assert exc_info.value.status_code == 400
        assert "Unsupported MIME type" in exc_info.value.detail

    def test_validate_video_file_invalid_extension(self):
        """Test validation failure with invalid extension."""
        upload_file = Mock(spec=UploadFile)
        upload_file.content_type = "video/mp4"
        upload_file.filename = "test.txt"
        
        with pytest.raises(HTTPException) as exc_info:
            validate_video_file(upload_file)
        
        assert exc_info.value.status_code == 400
        assert "Unsupported file extension" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_video_metadata_success(self):
        """Test successful video metadata extraction."""
        mock_probe_data = {
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "width": 1920,
                    "height": 1080,
                    "r_frame_rate": "30/1"
                }
            ],
            "format": {
                "duration": "120.5",
                "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
                "bit_rate": "2500000"
            }
        }
        
        with patch('app.utils.video_utils.asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (
                json.dumps(mock_probe_data).encode(),
                b""
            )
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process
            
            # Mock file stats
            with patch('app.utils.video_utils.Path.stat') as mock_stat:
                mock_stat.return_value.st_size = 1024000  # 1MB
                
                metadata = await get_video_metadata("test_video.mp4")
                
                assert metadata["duration"] == 120.5
                assert metadata["width"] == 1920
                assert metadata["height"] == 1080
                assert metadata["size_bytes"] == 1024000
                assert metadata["codec"] == "h264"
                assert metadata["fps"] == 30

    @pytest.mark.asyncio
    async def test_get_video_metadata_no_video_stream(self):
        """Test metadata extraction failure with no video stream."""
        mock_probe_data = {
            "streams": [
                {
                    "codec_type": "audio",
                    "codec_name": "aac"
                }
            ],
            "format": {
                "duration": "120.5",
                "format_name": "mov,mp4,m4a,3gp,3g2,mj2"
            }
        }
        
        with patch('app.utils.video_utils.asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()
            mock_process.communicate.return_value = (
                json.dumps(mock_probe_data).encode(),
                b""
            )
            mock_process.returncode = 0
            mock_subprocess.return_value = mock_process
            
            with pytest.raises(RuntimeError, match="No video stream found"):
                await get_video_metadata("test_video.mp4")

    @pytest.mark.asyncio
    async def test_get_video_middle_frame_time(self):
        """Test getting middle frame timestamp."""
        mock_metadata = {
            "duration": 120.0,
            "width": 1920,
            "height": 1080,
            "size_bytes": 1024000,
            "codec": "h264"
        }
        
        with patch('app.utils.video_utils.get_video_metadata') as mock_get_metadata:
            mock_get_metadata.return_value = mock_metadata
            
            middle_time = await get_video_middle_frame_time("test_video.mp4")
            
            assert middle_time == 60.0  # 120.0 / 2.0

    @pytest.mark.asyncio
    async def test_get_video_middle_frame_time_no_duration(self):
        """Test getting middle frame timestamp with zero duration."""
        mock_metadata = {
            "duration": 0.0,
            "width": 1920,
            "height": 1080,
            "size_bytes": 1024000,
            "codec": "h264"
        }
        
        with patch('app.utils.video_utils.get_video_metadata') as mock_get_metadata:
            mock_get_metadata.return_value = mock_metadata
            
            middle_time = await get_video_middle_frame_time("test_video.mp4")
            
            assert middle_time == 1.0  # fallback to 1 second

    def test_generate_video_filename(self):
        """Test video filename generation."""
        # Test with video ID
        filename = generate_video_filename("test video.mp4", 123)
        assert filename == "video_123.mp4"
        
        # Test without video ID
        filename = generate_video_filename("test video.mov")
        assert filename == "test_video.mov"
        
        # Test with invalid extension
        with pytest.raises(ValueError):
            generate_video_filename("test.txt")

    @pytest.mark.asyncio
    async def test_save_uploaded_video_success(self):
        """Test successful video file saving."""
        upload_file = Mock(spec=UploadFile)
        upload_file.read = AsyncMock(side_effect=[b"chunk1", b"chunk2", b""])
        
        destination_path = Path("/tmp/test_video.mp4")
        
        with patch('app.utils.video_utils.Path.open', create=True) as mock_open:
            mock_file = AsyncMock()
            mock_open.return_value.__aenter__.return_value = mock_file
            mock_file.write = AsyncMock()
            
            with patch('app.utils.video_utils.Path.mkdir'):
                await save_uploaded_video(upload_file, destination_path)
                
                # Verify file was written
                assert mock_file.write.call_count == 2

    @pytest.mark.asyncio
    async def test_save_uploaded_video_size_limit(self):
        """Test video file saving with size limit exceeded."""
        # Mock large file chunks that exceed limit
        large_chunk = b"x" * (200 * 1024 * 1024)  # 200MB chunk
        upload_file = Mock(spec=UploadFile)
        upload_file.read = AsyncMock(side_effect=[large_chunk, b""])
        
        destination_path = Path("/tmp/test_video.mp4")
        
        # Create a real file to test with
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.write(large_chunk)
        temp_file.close()
        
        try:
            # Use real file operations but mock the upload file reading
            with patch('app.utils.video_utils.Path.open', create=True) as mock_open:
                # Mock the file opening but allow real size checking
                def mock_file_open(mode, *args, **kwargs):
                    if 'w' in mode:
                        # Create a mock that simulates the size limit check
                        mock_file = AsyncMock()
                        
                        def mock_write(data):
                            # Simulate the size limit check
                            total_size = getattr(mock_file, '_total_size', 0) + len(data)
                            mock_file._total_size = total_size
                            if total_size > 500 * 1024 * 1024:  # 500MB limit
                                raise HTTPException(
                                    status_code=413,
                                    detail=f"Video file too large. Maximum size: {500}MB"
                                )
                        
                        mock_file.write = mock_write
                        mock_file._total_size = 0
                        return mock_file
                    else:
                        return mock_open.return_value
                
                mock_open.side_effect = mock_file_open
                
                with patch('app.utils.video_utils.Path.mkdir'):
                    with patch('app.utils.video_utils.Path.exists', return_value=True):
                        with patch('app.utils.video_utils.Path.unlink'):
                            with pytest.raises(HTTPException) as exc_info:
                                await save_uploaded_video(upload_file, destination_path)
                            
                            assert exc_info.value.status_code == 413
                            assert "Video file too large" in exc_info.value.detail
        finally:
            # Clean up temp file
            Path(temp_file.name).unlink(missing_ok=True)


class TestVideoUploadEndpoint:
    """Test video upload endpoint."""

    @pytest.mark.asyncio
    async def test_upload_single_video_success(self):
        """Test successful single video upload."""
        # Mock database session
        mock_db = Mock(spec=AsyncSession)
        mock_db.get = AsyncMock()
        mock_db.scalar = AsyncMock(return_value=0)  # No existing videos
        mock_db.add = Mock()
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Mock AR content
        mock_ar_content = Mock(spec=ARContent)
        mock_ar_content.company_id = 1
        mock_ar_content.project_id = 1
        mock_ar_content.unique_id = "test-uuid"
        mock_db.get.return_value = mock_ar_content
        
        # Mock upload file
        upload_file = Mock(spec=UploadFile)
        upload_file.filename = "test_video.mp4"
        upload_file.content_type = "video/mp4"
        upload_file.read = AsyncMock(side_effect=[b"chunk1", b"chunk2", b""])
        
        # Mock utility functions
        with patch('app.api.routes.videos.build_ar_content_storage_path') as mock_storage_path:
            mock_storage_path.return_value = Path("/tmp/storage")
            
            with patch('app.api.routes.videos.validate_video_file'):
                with patch('app.api.routes.videos.generate_video_filename', return_value="video_123.mp4"):
                    with patch('app.api.routes.videos.save_uploaded_video'):
                        with patch('app.api.routes.videos.get_video_metadata', return_value={
                            "duration": 120.0,
                            "width": 1920,
                            "height": 1080,
                            "size_bytes": 1024000,
                            "mime_type": "video/mp4"
                        }):
                            with patch('app.api.routes.videos.build_public_url', return_value="/storage/video_123.mp4"):
                                with patch('app.api.routes.videos.generate_video_thumbnail') as mock_task:
                                    mock_task.delay.return_value = None
                                    
                                    # Create video mock
                                    mock_video = Mock(spec=Video)
                                    mock_video.id = 123
                                    mock_video.title = "test_video.mp4"
                                    mock_video.video_url = "/storage/video_123.mp4"
                                    mock_video.video_path = "/tmp/storage/videos/video_123.mp4"
                                    mock_video.preview_url = None
                                    mock_video.duration = 120.0
                                    mock_video.width = 1920
                                    mock_video.height = 1080
                                    mock_video.size_bytes = 1024000
                                    mock_video.mime_type = "video/mp4"
                                    mock_video.status = "processing"
                                    mock_video.is_active = True
                                    mock_video.rotation_type = "none"
                                    mock_video.created_at = "2023-01-01T00:00:00Z"
                                    mock_video.updated_at = "2023-01-01T00:00:00Z"
                                    
                                    # Mock Video constructor
                                    with patch('app.api.routes.videos.Video', return_value=mock_video):
                                        result = await upload_videos(1, [upload_file], mock_db)
                                        
                                        assert result["message"] == "Successfully uploaded 1 video(s)"
                                        assert len(result["videos"]) == 1
                                        assert result["videos"][0]["id"] == 123
                                        assert result["videos"][0]["status"] == "processing"
                                        assert result["ar_content"]["active_video_id"] == 123

    @pytest.mark.asyncio
    async def test_upload_video_ar_content_not_found(self):
        """Test video upload with non-existent AR content."""
        mock_db = Mock(spec=AsyncSession)
        mock_db.get = AsyncMock(return_value=None)
        
        upload_file = Mock(spec=UploadFile)
        upload_file.filename = "test_video.mp4"
        upload_file.content_type = "video/mp4"
        
        with pytest.raises(HTTPException) as exc_info:
            await upload_videos(999, [upload_file], mock_db)
        
        assert exc_info.value.status_code == 404
        assert "AR content not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_upload_video_invalid_format(self):
        """Test video upload with invalid file format."""
        mock_db = Mock(spec=AsyncSession)
        mock_ar_content = Mock(spec=ARContent)
        mock_db.get.return_value = mock_ar_content
        
        upload_file = Mock(spec=UploadFile)
        upload_file.filename = "test.txt"
        upload_file.content_type = "text/plain"
        
        with pytest.raises(HTTPException) as exc_info:
            await upload_videos(1, [upload_file], mock_db)
        
        assert exc_info.value.status_code == 400
        assert "Unsupported MIME type" in exc_info.value.detail


class TestVideoPreviewTask:
    """Test video preview generation task."""

    @pytest.mark.asyncio
    async def test_generate_video_thumbnail_task_success(self):
        """Test successful video thumbnail generation task."""
        # Mock video
        mock_video = Mock(spec=Video)
        mock_video.id = 123
        mock_video.video_path = "/tmp/test_video.mp4"
        mock_video.preview_url = None
        mock_video.status = "processing"
        
        # Mock AR content
        mock_ar_content = Mock(spec=ARContent)
        mock_ar_content.company_id = 1
        mock_ar_content.project_id = 1
        mock_ar_content.unique_id = "test-uuid"
        
        # Mock company
        mock_company = Mock(spec=Company)
        
        # Mock database session
        mock_db = Mock(spec=AsyncSession)
        mock_db.get = AsyncMock(side_effect=[mock_video, mock_ar_content, mock_company])
        mock_db.commit = AsyncMock()
        
        # Mock Path.exists
        with patch('app.tasks.preview_tasks.Path.exists', return_value=True):
            # Mock storage path building
            with patch('app.tasks.preview_tasks.build_ar_content_storage_path', return_value=Path("/tmp/storage")):
                # Mock middle frame time
                with patch('app.tasks.preview_tasks.get_video_middle_frame_time', return_value=60.0):
                    # Mock thumbnail service
                    with patch('app.tasks.preview_tasks.thumbnail_service.generate_video_thumbnail') as mock_thumbnail:
                        mock_thumbnail.return_value = {
                            "status": "ready",
                            "thumbnail_url": "/storage/previews/video_123_preview.jpg"
                        }
                        
                        # Mock database context manager
                        with patch('app.tasks.preview_tasks.AsyncSessionLocal') as mock_session:
                            mock_session.return_value.__aenter__.return_value = mock_db
                            
                            # Import and run the task
                            from app.tasks.preview_tasks import generate_video_thumbnail
                            
                            result = generate_video_thumbnail(123)
                            
                            # Verify the task was processed
                            assert mock_video.preview_url == "/storage/previews/video_123_preview.jpg"
                            assert mock_video.status == "active"
                            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_video_thumbnail_task_video_not_found(self):
        """Test thumbnail generation task with non-existent video."""
        # Mock database session
        mock_db = Mock(spec=AsyncSession)
        mock_db.get = AsyncMock(return_value=None)
        
        with patch('app.tasks.preview_tasks.AsyncSessionLocal') as mock_session:
            mock_session.return_value.__aenter__.return_value = mock_db
            
            from app.tasks.preview_tasks import generate_video_thumbnail
            
            task = generate_video_thumbnail.get_bound_task()
            with pytest.raises(ValueError, match="Video 999 not found"):
                await task._generate()

    @pytest.mark.asyncio
    async def test_generate_video_thumbnail_task_file_not_found(self):
        """Test thumbnail generation task with missing video file."""
        # Mock video
        mock_video = Mock(spec=Video)
        mock_video.id = 123
        mock_video.video_path = "/tmp/nonexistent_video.mp4"
        
        # Mock database session
        mock_db = Mock(spec=AsyncSession)
        mock_db.get = AsyncMock(return_value=mock_video)
        
        with patch('app.tasks.preview_tasks.Path.exists', return_value=False):
            with patch('app.tasks.preview_tasks.AsyncSessionLocal') as mock_session:
                mock_session.return_value.__aenter__.return_value = mock_db
                
                from app.tasks.preview_tasks import generate_video_thumbnail
                
                task = generate_video_thumbnail.get_bound_task()
                with pytest.raises(FileNotFoundError, match="Video file not found"):
                    await task._generate()


if __name__ == "__main__":
    pytest.main([__file__])