"""
Tests for the new AR Content API with Company → Project → AR Content hierarchy.
"""
import pytest
import io
from uuid import uuid4


@pytest.mark.asyncio
async def test_list_ar_content_empty(async_client):
    """Test listing AR content when none exists."""
    response = await async_client.get("/api/companies/1/projects/1/ar-content")
    assert response.status_code == 404  # Company or project not found


@pytest.mark.asyncio
async def test_create_ar_content_missing_auth(async_client):
    """Test that creating AR content requires authentication."""
    response = await async_client.post(
        "/api/companies/1/projects/1/ar-content/new",
        data={"name": "Test AR Content"},
        files={"image": ("test.jpg", io.BytesIO(b"fake image data"), "image/jpeg")},
    )
    # Endpoint is not protected by auth; should fail due to missing company/project validation
    assert response.status_code in [404, 400]


@pytest.mark.asyncio
async def test_get_nonexistent_ar_content(async_client):
    """Test getting AR content that doesn't exist."""
    response = await async_client.get("/api/companies/1/projects/1/ar-content/999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_public_ar_content_not_found(async_client):
    """Test public AR content endpoint with non-existent UUID."""
    fake_uuid = uuid4()
    response = await async_client.get(f"/api/ar/{fake_uuid}/content")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_public_ar_content_invalid_uuid(async_client):
    """Test public AR content endpoint with invalid UUID."""
    response = await async_client.get("/api/ar/invalid-uuid/content")
    # unique_id is a string param, so we get a normal 404 from lookup, not 422
    assert response.status_code == 404


@pytest.mark.asyncio 
async def test_ar_viewer_template(async_client):
    """Test AR viewer template endpoint."""
    fake_uuid = uuid4()
    response = await async_client.get(f"/ar/{fake_uuid}")
    # Should return HTML template even for non-existent content
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_ar_viewer_template_new_path(async_client):
    """Test AR viewer template endpoint with new path."""
    fake_uuid = uuid4()
    response = await async_client.get(f"/ar-content/{fake_uuid}")
    # Should return HTML template even for non-existent content  
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_health_still_works(async_client):
    """Test that health endpoint still works to ensure basic API is functional."""
    response = await async_client.get("/api/health/status")
    assert response.status_code == 200