import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_health_status():
    async with AsyncClient(base_url="http://test", transport=httpx.ASGITransport(app=app)) as client:
        response = await client.get("/api/health/status")
        assert response.status_code == 200
        data = response.json()
        assert "overall" in data

@pytest.mark.asyncio
async def test_list_companies_include_default():
    async with AsyncClient(base_url="http://test", transport=httpx.ASGITransport(app=app)) as client:
        response = await client.get("/api/companies/?include_default=true")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_list_companies_exclude_default():
    async with AsyncClient(base_url="http://test", transport=httpx.ASGITransport(app=app)) as client:
        response = await client.get("/api/companies/?include_default=false")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_get_company_not_found():
    async with AsyncClient(base_url="http://test", transport=httpx.ASGITransport(app=app)) as client:
        response = await client.get("/api/companies/99999")
        assert response.status_code == 404

@pytest.mark.skip(reason="Requires external storage provider setup (MinIO/Yandex).")
@pytest.mark.asyncio
async def test_create_company_minio():
    # Placeholder for full creation flow requiring provider setup
    pass

@pytest.mark.asyncio
async def test_list_projects():
    async with AsyncClient(base_url="http://test", transport=httpx.ASGITransport(app=app)) as client:
        response = await client.get("/api/projects/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_get_project_not_found():
    async with AsyncClient(base_url="http://test", transport=httpx.ASGITransport(app=app)) as client:
        response = await client.get("/api/projects/99999")
        assert response.status_code == 404

@pytest.mark.asyncio
async def test_get_company_projects_not_found():
    async with AsyncClient(base_url="http://test", transport=httpx.ASGITransport(app=app)) as client:
        response = await client.get("/api/companies/99999/projects")
        assert response.status_code == 404

@pytest.mark.asyncio
async def test_company_analytics():
    async with AsyncClient(base_url="http://test", transport=httpx.ASGITransport(app=app)) as client:
        # Test with company ID 1 (should exist from seed data)
        response = await client.get("/api/companies/1/analytics")
        assert response.status_code == 200
        data = response.json()
        assert "company_id" in data
        assert data["company_id"] == 1
        assert "total_views" in data
        assert "unique_sessions" in data
        assert "active_projects" in data
        assert "active_content" in data
