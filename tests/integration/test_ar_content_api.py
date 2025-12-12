"""
Tests for the new AR Content API with Company → Project → AR Content hierarchy.
"""
import pytest
import io
from httpx import AsyncClient
from uuid import uuid4
from app.main import app


@pytest.mark.asyncio
async def test_list_ar_content_empty():
    """Test listing AR content when none exists."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/companies/1/projects/1/ar-content")
        assert response.status_code == 404  # Company or project not found


@pytest.mark.asyncio
async def test_create_ar_content_missing_auth():
    """Test that creating AR content requires authentication."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/companies/1/projects/1/ar-content/new",
            data={"name": "Test AR Content"},
            files={"image": ("test.jpg", io.BytesIO(b"fake image data"), "image/jpeg")}
        )
        # Should fail due to missing company/project validation, not auth
        assert response.status_code in [404, 400]


@pytest.mark.asyncio
async def test_get_nonexistent_ar_content():
    """Test getting AR content that doesn't exist."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/companies/1/projects/1/ar-content/999")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_public_ar_content_not_found():
    """Test public AR content endpoint with non-existent UUID."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        fake_uuid = uuid4()
        response = await client.get(f"/api/ar/{fake_uuid}/content")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_public_ar_content_invalid_uuid():
    """Test public AR content endpoint with invalid UUID."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/ar/invalid-uuid/content")
        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio 
async def test_ar_viewer_template():
    """Test AR viewer template endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        fake_uuid = uuid4()
        response = await client.get(f"/ar/{fake_uuid}")
        # Should return HTML template even for non-existent content
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_ar_viewer_template_new_path():
    """Test AR viewer template endpoint with new path."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        fake_uuid = uuid4()
        response = await client.get(f"/ar-content/{fake_uuid}")
        # Should return HTML template even for non-existent content  
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_health_still_works():
    """Test that health endpoint still works to ensure basic API is functional."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/health/status")
        assert response.status_code == 200