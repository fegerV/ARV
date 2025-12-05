import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_health_status():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/health/status")
        assert response.status_code == 200
        data = response.json()
        assert "overall" in data

@pytest.mark.asyncio
async def test_list_companies_include_default():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/companies/?include_default=true")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

@pytest.mark.skip(reason="Requires external storage provider setup (MinIO/Yandex).")
@pytest.mark.asyncio
async def test_create_company_minio():
    # Placeholder for full creation flow requiring provider setup
    pass
