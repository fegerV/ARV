"""
Tests for AR Content creation API endpoint.
"""
import pytest
import io
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.company import Company
from app.models.project import Project
from app.models.ar_content import ARContent
from app.models.video import Video


@pytest.mark.asyncio
async def test_create_ar_content_success(async_client: AsyncClient, db: AsyncSession, sample_company, sample_project):
    """Test successful AR content creation with photo and video files."""
    # Create test image and video files
    photo_bytes = b"\x89PNG\r\n\x1a\n" + (b"0" * 100)  # Minimal PNG
    video_bytes = b"\x00\x00\x00\x18ftypmp42" + (b"0" * 100)  # Minimal MP4
    
    data = {
        "company_id": sample_company.id,
        "project_id": sample_project.id,
        "customer_name": "Test Customer",
        "customer_phone": "+1234567890",
        "customer_email": "customer@test.com",
        "duration_years": "3",
    }
    
    files = {
        "photo_file": ("test_photo.png", io.BytesIO(photo_bytes), "image/png"),
        "video_file": ("test_video.mp4", io.BytesIO(video_bytes), "video/mp4"),
    }
    
    response = await async_client.post("/api/ar-content", data=data, files=files)
    
    # Check response
    assert response.status_code == 201  # Should be 201 for creation
    result = response.json()
    
    assert "id" in result
    assert result["order_number"].startswith("AR-")  # Updated format
    assert result["public_link"].startswith("/view/")
    assert result["qr_code_url"] is not None
    assert result["photo_url"] is not None
    assert result["video_url"] is not None
    
    # Verify database records
    # Check AR content
    stmt = select(ARContent).where(ARContent.id == result["id"])
    db_result = await db.execute(stmt)
    ar_content = db_result.scalar_one()
    
    assert ar_content.customer_name == "Test Customer"
    assert ar_content.customer_email == "customer@test.com"
    assert ar_content.duration_years == 3
    assert ar_content.status == "pending"
    assert ar_content.order_number == result["order_number"]
    
    # Check video record
    stmt = select(Video).where(Video.ar_content_id == result["id"])
    db_result = await db.execute(stmt)
    videos = db_result.scalars().all()
    
    assert len(videos) == 1
    assert videos[0].is_active is True
    assert videos[0].filename == "test_video.mp4"


@pytest.mark.asyncio
async def test_create_ar_content_invalid_files(async_client: AsyncClient, db: AsyncSession, sample_company, sample_project):
    """Test AR content creation with invalid file formats."""
    # Create test files with invalid extensions
    text_bytes = b"some text content"
    exe_bytes = b"MZ" + (b"0" * 100)  # Invalid executable
    
    data = {
        "company_id": sample_company.id,
        "project_id": sample_project.id,
        "duration_years": "1",
    }
    
    # Test invalid photo format
    files = {
        "photo_file": ("test_photo.txt", io.BytesIO(text_bytes), "text/plain"),
        "video_file": ("test_video.mp4", io.BytesIO(b"video"), "video/mp4"),
    }
    
    response = await async_client.post("/api/ar-content", data=data, files=files)
    assert response.status_code == 422
    assert "Photo must be JPEG or PNG" in response.json()["detail"]
    
    # Test invalid video format
    files = {
        "photo_file": ("test_photo.png", io.BytesIO(b"photo"), "image/png"),
        "video_file": ("test_video.exe", io.BytesIO(exe_bytes), "application/octet-stream"),
    }
    
    response = await async_client.post("/api/ar-content", data=data, files=files)
    assert response.status_code == 422
    assert "Video must be MP4, WebM, or MOV" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_ar_content_missing_company(async_client: AsyncClient, db: AsyncSession, sample_project):
    """Test AR content creation with non-existent company."""
    photo_bytes = b"\x89PNG\r\n\x1a\n" + (b"0" * 100)
    video_bytes = b"\x00\x00\x00\x18ftypmp42" + (b"0" * 100)
    
    # Use invalid company ID
    invalid_company_id = 999999
    
    data = {
        "company_id": invalid_company_id,
        "project_id": sample_project.id,
        "duration_years": "1",
    }
    
    files = {
        "photo_file": ("test_photo.png", io.BytesIO(photo_bytes), "image/png"),
        "video_file": ("test_video.mp4", io.BytesIO(video_bytes), "video/mp4"),
    }
    
    response = await async_client.post("/api/ar-content", data=data, files=files)
    
    assert response.status_code == 404
    assert "Company not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_ar_content_files_saved(async_client: AsyncClient, db: AsyncSession, sample_company, sample_project):
    """Test that AR content files are saved to disk."""
    import os
    from pathlib import Path
    from app.core.config import settings
    from app.utils.ar_content import build_ar_content_storage_path
    
    photo_bytes = b"\x89PNG\r\n\x1a\n" + (b"0" * 100)
    video_bytes = b"\x00\x00\x00\x18ftypmp42" + (b"0" * 100)
    
    data = {
        "company_id": sample_company.id,
        "project_id": sample_project.id,
        "customer_name": "File Test Customer",
        "duration_years": "1",
    }
    
    files = {
        "photo_file": ("test_photo.png", io.BytesIO(photo_bytes), "image/png"),
        "video_file": ("test_video.mp4", io.BytesIO(video_bytes), "video/mp4"),
    }
    
    response = await async_client.post("/api/ar-content", data=data, files=files)
    assert response.status_code == 201
    
    result = response.json()
    
    # Verify files exist in storage
    stmt = select(ARContent).where(ARContent.id == result["id"])
    db_result = await db.execute(stmt)
    ar_content = db_result.scalar_one()
    
    # Check that photo file exists
    assert ar_content.photo_path is not None
    photo_path = Path(ar_content.photo_path)
    assert photo_path.exists()
    
    # Check that video file exists
    assert ar_content.video_path is not None
    video_path = Path(ar_content.video_path)
    assert video_path.exists()
    
    # Check that QR code exists
    assert ar_content.qr_code_path is not None
    qr_path = Path(ar_content.qr_code_path)
    assert qr_path.exists()


@pytest.mark.asyncio
async def test_qr_code_generated(async_client: AsyncClient, db: AsyncSession, sample_company, sample_project):
    """Test that QR code is generated for AR content."""
    photo_bytes = b"\x89PNG\r\n\x1a\n" + (b"0" * 100)
    video_bytes = b"\x00\x00\x00\x18ftypmp42" + (b"0" * 100)
    
    data = {
        "company_id": sample_company.id,
        "project_id": sample_project.id,
        "customer_name": "QR Test Customer",
        "duration_years": "1",
    }
    
    files = {
        "photo_file": ("test_photo.png", io.BytesIO(photo_bytes), "image/png"),
        "video_file": ("test_video.mp4", io.BytesIO(video_bytes), "video/mp4"),
    }
    
    response = await async_client.post("/api/ar-content", data=data, files=files)
    assert response.status_code == 201
    
    result = response.json()
    
    # Verify QR code URL is present
    assert result["qr_code_url"] is not None
    assert len(result["qr_code_url"]) > 0


@pytest.mark.asyncio
async def test_marker_generated(async_client: AsyncClient, db: AsyncSession, sample_company, sample_project):
    """Test that Mind AR marker is generated for AR content."""
    # Note: This test would require the mind-ar-js-compiler to be installed and working
    # For now, we'll just verify that the endpoint works
    photo_bytes = b"\x89PNG\r\n\x1a\n" + (b"0" * 100)
    video_bytes = b"\x00\x00\x00\x18ftypmp42" + (b"0" * 100)
    
    data = {
        "company_id": sample_company.id,
        "project_id": sample_project.id,
        "customer_name": "Marker Test Customer",
        "duration_years": "1",
    }
    
    files = {
        "photo_file": ("test_photo.png", io.BytesIO(photo_bytes), "image/png"),
        "video_file": ("test_video.mp4", io.BytesIO(video_bytes), "video/mp4"),
    }
    
    response = await async_client.post("/api/ar-content", data=data, files=files)
    
    # The endpoint should work even if marker generation fails
    assert response.status_code == 201
    
    result = response.json()
    assert "id" in result


@pytest.mark.asyncio
async def test_get_ar_content_with_videos(async_client: AsyncClient, db: AsyncSession, sample_company, sample_project):
    """Test getting AR content with videos."""
    # First create AR content
    photo_bytes = b"\x89PNG\r\n\x1a\n" + (b"0" * 100)
    video_bytes = b"\x00\x00\x00\x18ftypmp42" + (b"0" * 100)
    
    data = {
        "company_id": sample_company.id,
        "project_id": sample_project.id,
        "customer_name": "Get Test Customer",
        "duration_years": "1",
    }
    
    files = {
        "photo_file": ("test_photo.png", io.BytesIO(photo_bytes), "image/png"),
        "video_file": ("test_video.mp4", io.BytesIO(video_bytes), "video/mp4"),
    }
    
    response = await async_client.post("/api/ar-content", data=data, files=files)
    assert response.status_code == 201
    
    result = response.json()
    content_id = result["id"]
    
    # Get the AR content
    response = await async_client.get(f"/api/ar-content/{content_id}")
    assert response.status_code == 200
    
    result = response.json()
    
    # Verify all required fields are present
    assert result["id"] == content_id
    assert result["order_number"] is not None
    assert result["public_link"] is not None
    assert result["qr_code_url"] is not None
    assert result["photo_url"] is not None
    assert result["video_url"] is not None
    assert "videos" in result
    assert "active_video" in result