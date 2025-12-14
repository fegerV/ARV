"""
Integration tests for AR Content API endpoints.
"""
import pytest
import io
import uuid
import os
from pathlib import Path
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.company import Company
from app.models.project import Project
from app.models.ar_content import ARContent
from app.models.video import Video


@pytest.mark.asyncio
async def test_list_ar_content_empty(async_client: AsyncClient, db: AsyncSession):
    """Test listing AR content when empty."""
    response = await async_client.get("/api/ar-content")
    
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["total_pages"] == 0


@pytest.mark.asyncio
async def test_create_ar_content_uploads_files_to_media_root(async_client: AsyncClient, db: AsyncSession, sample_company, sample_project):
    # Create minimal PNG and MP4 payloads (content doesn't need to be valid video for file-save test)
    photo_bytes = b"\x89PNG\r\n\x1a\n" + (b"0" * 32)
    video_bytes = b"\x00\x00\x00\x18ftypmp42" + (b"0" * 64)

    data = {
        "company_id": str(sample_company.id),
        "project_id": str(sample_project.id),
        "customer_name": "Uploader",
        "duration_years": "1",
    }
    files = {
        "photo_file": ("photo.png", io.BytesIO(photo_bytes), "image/png"),
        "video_file": ("video.mp4", io.BytesIO(video_bytes), "video/mp4"),
    }

    res = await async_client.post("/api/ar-content", data=data, files=files)
    assert res.status_code == 200
    created = res.json()
    content_id = created["id"]

    # Verify DB record has paths set
    row = await db.execute(select(ARContent).where(ARContent.id == content_id))
    ac = row.scalar_one()
    assert ac.photo_path
    assert ac.video_path

    # Verify files exist in MEDIA_ROOT
    media_root = os.environ.get("MEDIA_ROOT")
    assert media_root
    assert Path(ac.photo_path).exists()
    assert Path(ac.video_path).exists()
    assert str(Path(ac.photo_path)).startswith(str(Path(media_root)))
    assert str(Path(ac.video_path)).startswith(str(Path(media_root)))


@pytest.mark.asyncio
async def test_marker_endpoint_serves_targets_mind(async_client: AsyncClient):
    media_root = os.environ.get("MEDIA_ROOT")
    assert media_root

    # Create fake marker file
    content_id = "test-content-id"
    marker_path = Path(media_root) / "markers" / content_id / "targets.mind"
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_bytes = b"MIND" + (b"0" * 32)
    marker_path.write_bytes(marker_bytes)

    res = await async_client.get(f"/api/ar-content/{content_id}/marker")
    assert res.status_code == 200
    assert res.content == marker_bytes


@pytest.mark.asyncio
async def test_list_ar_content_with_data(async_client: AsyncClient, db: AsyncSession, sample_company, sample_project):
    """Test listing AR content with sample data."""
    # Create sample AR content
    ar_content = ARContent(
        project_id=sample_project.id,
        unique_id=uuid.uuid4(),
        order_number="AR-20250624-0001",
        customer_name="John Doe",
        customer_email="john@example.com",
        customer_phone="+1234567890",
        duration_years=1,
        status="pending"
    )
    db.add(ar_content)
    await db.commit()
    
    response = await async_client.get("/api/ar-content")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    
    item = data["items"][0]
    assert item["order_number"] == "AR-20250624-0001"
    assert item["company_name"] == sample_company.name
    assert item["project_name"] == sample_project.name
    assert item["customer_name"] == "John Doe"
    assert item["customer_email"] == "john@example.com"
    assert item["status"] == "pending"
    assert "_links" in item


@pytest.mark.asyncio
async def test_list_ar_content_with_filters(async_client: AsyncClient, db: AsyncSession, sample_company, sample_project):
    """Test listing AR content with filters."""
    # Create multiple AR content items
    for i in range(3):
        ar_content = ARContent(
            project_id=sample_project.id,
            unique_id=uuid.uuid4(),
            order_number=f"AR-20250624-{i+1:04d}",
            customer_name=f"Customer {i+1}",
            customer_email=f"customer{i+1}@example.com",
            status="pending" if i < 2 else "active",
            duration_years=1
        )
        db.add(ar_content)
    await db.commit()
    
    # Test status filter
    response = await async_client.get("/api/ar-content?status=pending")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    
    # Test search filter
    response = await async_client.get("/api/ar-content?search=Customer 1")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["customer_name"] == "Customer 1"
    
    # Test pagination
    response = await async_client.get("/api/ar-content?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total_pages"] == 2


@pytest.mark.asyncio
async def test_create_ar_content_success(async_client: AsyncClient, db: AsyncSession, sample_company, sample_project):
    """Test successful AR content creation."""
    # Create test image file
    image_content = io.BytesIO(b"fake image content")
    image_content.name = "test.jpg"
    
    data = {
        "company_id": sample_company.id,
        "project_id": str(sample_project.id),
        "customer_name": "Jane Smith",
        "customer_email": "jane@example.com",
        "customer_phone": "+9876543210",
        "duration_years": 3
    }
    
    files = {
        "photo_file": ("test.jpg", image_content, "image/jpeg")
    }
    
    response = await async_client.post("/api/ar-content", data=data, files=files)
    
    assert response.status_code == 200
    result = response.json()
    assert "id" in result
    assert result["order_number"].startswith("AR-2025")
    assert result["public_link"].startswith("/ar-content/")
    assert result["qr_code_url"] is not None
    assert result["photo_url"] is not None
    
    # Verify database record
    stmt = select(ARContent).where(ARContent.order_number == result["order_number"])
    db_result = await db.execute(stmt)
    ar_content = db_result.scalar_one()
    
    assert ar_content.customer_name == "Jane Smith"
    assert ar_content.customer_email == "jane@example.com"
    assert ar_content.duration_years == 3
    assert ar_content.status == "pending"


@pytest.mark.asyncio
async def test_create_ar_content_validation_errors(async_client: AsyncClient, db: AsyncSession, sample_company, sample_project):
    """Test AR content creation with validation errors."""
    # Test invalid email
    image_content = io.BytesIO(b"fake image content")
    image_content.name = "test.jpg"
    
    data = {
        "company_id": sample_company.id,
        "project_id": str(sample_project.id),
        "customer_email": "invalid-email",
        "duration_years": 2  # Invalid duration
    }
    
    files = {
        "photo_file": ("test.jpg", image_content, "image/jpeg")
    }
    
    response = await async_client.post("/api/ar-content", data=data, files=files)
    
    # Should return validation error for either email or duration
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_create_ar_content_invalid_file_type(async_client: AsyncClient, db: AsyncSession, sample_company, sample_project):
    """Test AR content creation with invalid file type."""
    # Create test file with invalid extension
    file_content = io.BytesIO(b"fake file content")
    file_content.name = "test.txt"
    
    data = {
        "company_id": sample_company.id,
        "project_id": str(sample_project.id),
    }
    
    files = {
        "photo_file": ("test.txt", file_content, "text/plain")
    }
    
    response = await async_client.post("/api/ar-content", data=data, files=files)
    
    assert response.status_code == 400
    assert "Photo must be JPG or PNG" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_ar_content_details(async_client: AsyncClient, db: AsyncSession, sample_company, sample_project):
    """Test getting AR content details."""
    # Create sample AR content
    ar_content = ARContent(
        project_id=sample_project.id,
        unique_id=uuid.uuid4(),
        order_number="AR-20250624-0001",
        customer_name="John Doe",
        customer_email="john@example.com",
        duration_years=1,
        status="active",
        photo_url="/storage/photo.jpg",
        video_url="/storage/video.mp4",
        qr_code_url="/storage/qr.png"
    )
    db.add(ar_content)
    await db.commit()
    
    response = await async_client.get(f"/api/ar-content/{ar_content.id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(ar_content.id)
    assert data["order_number"] == "AR-20250624-0001"
    assert data["company_name"] == sample_company.name
    assert data["project_name"] == sample_project.name
    assert data["customer_name"] == "John Doe"
    assert data["status"] == "active"
    assert data["photo_url"] == "/storage/photo.jpg"
    assert data["video_url"] == "/storage/video.mp4"
    assert data["qr_code_url"] == "/storage/qr.png"
    assert "videos" in data
    assert "stats" in data
    assert "_links" in data


@pytest.mark.asyncio
async def test_get_ar_content_not_found(async_client: AsyncClient):
    """Test getting non-existent AR content."""
    fake_id = str(uuid.uuid4())
    response = await async_client.get(f"/api/ar-content/{fake_id}")
    
    assert response.status_code == 404
    assert "AR content not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_ar_content(async_client: AsyncClient, db: AsyncSession, sample_company, sample_project):
    """Test updating AR content."""
    # Create sample AR content
    ar_content = ARContent(
        project_id=sample_project.id,
        unique_id=uuid.uuid4(),
        order_number="AR-20250624-0001",
        customer_name="John Doe",
        customer_email="john@example.com",
        duration_years=1,
        status="pending"
    )
    db.add(ar_content)
    await db.commit()
    
    update_data = {
        "customer_name": "Jane Smith",
        "customer_email": "jane.smith@example.com",
        "status": "active",
        "duration_years": 3
    }
    
    response = await async_client.put(f"/api/ar-content/{ar_content.id}", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["customer_name"] == "Jane Smith"
    assert data["customer_email"] == "jane.smith@example.com"
    assert data["status"] == "active"
    assert data["duration_years"] == 3
    
    # Verify database update
    await db.refresh(ar_content)
    assert ar_content.customer_name == "Jane Smith"
    assert ar_content.status == "active"


@pytest.mark.asyncio
async def test_upload_ar_content_video(async_client: AsyncClient, db: AsyncSession, sample_company, sample_project):
    """Test uploading video for AR content."""
    # Create sample AR content
    ar_content = ARContent(
        project_id=sample_project.id,
        unique_id=uuid.uuid4(),
        order_number="AR-20250624-0001"
    )
    db.add(ar_content)
    await db.commit()
    
    # Create test video file
    video_content = io.BytesIO(b"fake video content")
    video_content.name = "test.mp4"
    
    files = {
        "video_file": ("test.mp4", video_content, "video/mp4")
    }
    data = {
        "set_as_active": "true"
    }
    
    response = await async_client.post(f"/api/ar-content/{ar_content.id}/videos", data=data, files=files)
    
    assert response.status_code == 200
    result = response.json()
    assert "id" in result
    assert result["filename"].endswith(".mp4")
    assert result["is_active"] is True
    assert "_links" in result
    
    # Verify database record
    stmt = select(Video).where(Video.id == result["id"])
    db_result = await db.execute(stmt)
    video = db_result.scalar_one()
    assert video.ar_content_id == ar_content.id
    
    # Verify AR content updated with active video
    await db.refresh(ar_content)
    assert ar_content.active_video_id == video.id


@pytest.mark.asyncio
async def test_upload_ar_content_video_invalid_type(async_client: AsyncClient, db: AsyncSession, sample_company, sample_project):
    """Test uploading video with invalid file type."""
    # Create sample AR content
    ar_content = ARContent(
        project_id=sample_project.id,
        unique_id=uuid.uuid4(),
        order_number="AR-20250624-0001"
    )
    db.add(ar_content)
    await db.commit()
    
    # Create test file with invalid extension
    file_content = io.BytesIO(b"fake file content")
    file_content.name = "test.txt"
    
    files = {
        "video_file": ("test.txt", file_content, "text/plain")
    }
    
    response = await async_client.post(f"/api/ar-content/{ar_content.id}/videos", files=files)
    
    assert response.status_code == 400
    assert "Video must be MP4" in response.json()["detail"]


@pytest.mark.asyncio
async def test_set_active_video(async_client: AsyncClient, db: AsyncSession, sample_company, sample_project):
    """Test setting video as active."""
    # Create sample AR content and video
    ar_content = ARContent(
        project_id=sample_project.id,
        unique_id=uuid.uuid4(),
        order_number="AR-20250624-0001"
    )
    db.add(ar_content)
    await db.commit()
    
    video = Video(
        ar_content_id=ar_content.id,
        filename="test.mp4"
    )
    db.add(video)
    await db.commit()
    
    response = await async_client.put(f"/api/ar-content/{ar_content.id}/videos/{video.id}/set-active")
    
    assert response.status_code == 200
    assert "set as active" in response.json()["message"].lower()
    
    # Verify database update
    await db.refresh(ar_content)
    assert ar_content.active_video_id == video.id


@pytest.mark.asyncio
async def test_delete_ar_content_video(async_client: AsyncClient, db: AsyncSession, sample_company, sample_project):
    """Test deleting video from AR content."""
    # Create sample AR content and multiple videos
    ar_content = ARContent(
        project_id=sample_project.id,
        unique_id=uuid.uuid4(),
        order_number="AR-20250624-0001"
    )
    db.add(ar_content)
    await db.commit()
    
    video1 = Video(
        ar_content_id=ar_content.id,
        filename="test1.mp4"
    )
    video2 = Video(
        ar_content_id=ar_content.id,
        filename="test2.mp4"
    )
    db.add_all([video1, video2])
    await db.commit()
    
    # Set first video as active
    ar_content.active_video_id = video1.id
    await db.commit()
    
    # Delete second video (not active)
    response = await async_client.delete(f"/api/ar-content/{ar_content.id}/videos/{video2.id}")
    
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]
    
    # Verify deletion
    stmt = select(Video).where(Video.id == video2.id)
    db_result = await db.execute(stmt)
    assert db_result.scalar_one_or_none() is None
    
    # Active video should be unchanged
    await db.refresh(ar_content)
    assert ar_content.active_video_id == video1.id


@pytest.mark.asyncio
async def test_delete_last_video_fails(async_client: AsyncClient, db: AsyncSession, sample_company, sample_project):
    """Test that deleting the last video fails."""
    # Create sample AR content with single video
    ar_content = ARContent(
        project_id=sample_project.id,
        unique_id=uuid.uuid4(),
        order_number="AR-20250624-0001"
    )
    db.add(ar_content)
    await db.commit()
    
    video = Video(
        ar_content_id=ar_content.id,
        filename="test.mp4"
    )
    db.add(video)
    await db.commit()
    
    response = await async_client.delete(f"/api/ar-content/{ar_content.id}/videos/{video.id}")
    
    assert response.status_code == 400
    assert "Cannot delete the last video" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_ar_content(async_client: AsyncClient, db: AsyncSession, sample_company, sample_project):
    """Test deleting AR content."""
    # Create sample AR content
    ar_content = ARContent(
        project_id=sample_project.id,
        unique_id=uuid.uuid4(),
        order_number="AR-20250624-0001"
    )
    db.add(ar_content)
    await db.commit()
    
    response = await async_client.delete(f"/api/ar-content/{ar_content.id}")
    
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]
    
    # Verify deletion
    stmt = select(ARContent).where(ARContent.id == ar_content.id)
    db_result = await db.execute(stmt)
    assert db_result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_list_ar_content_videos(async_client: AsyncClient, db: AsyncSession, sample_company, sample_project):
    """Test listing videos for AR content."""
    # Create sample AR content
    ar_content = ARContent(
        project_id=sample_project.id,
        unique_id=uuid.uuid4(),
        order_number="AR-20250624-0001"
    )
    db.add(ar_content)
    await db.commit()
    
    # Create multiple videos
    videos = [
        Video(ar_content_id=ar_content.id, filename=f"video{i}.mp4")
        for i in range(3)
    ]
    db.add_all(videos)
    await db.commit()
    
    # Set second video as active
    ar_content.active_video_id = videos[1].id
    await db.commit()
    
    response = await async_client.get(f"/api/ar-content/{ar_content.id}/videos")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    
    # Check that second video is marked as active
    active_items = [item for item in data["items"] if item["is_active"]]
    assert len(active_items) == 1
    assert active_items[0]["filename"] == "video1.mp4"
    
    # Check _links in each item
    for item in data["items"]:
        assert "_links" in item
        assert "set_active" in item["_links"]
        assert "download" in item["_links"]
        assert "delete" in item["_links"]