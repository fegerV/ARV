import httpx
import pytest


def test_companies_and_projects_routes_are_registered():
    from app.main import app

    routes = {route.path for route in app.routes}

    assert "/api/companies" in routes
    assert "/api/companies/{company_id}" in routes
    assert "/api/companies/{company_id}/yandex-auth-url" in routes
    assert "/api/projects" in routes
    assert "/api/projects/{project_id}" in routes
    assert "/api/projects/by-company/{company_id}" in routes
    assert "/api/companies/{company_id}/projects" in routes


@pytest.mark.asyncio
async def test_companies_api_endpoints_require_auth():
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        responses = [
            await client.get("/api/companies"),
            await client.get("/api/companies/1"),
            await client.post("/api/companies", json={"name": "Test Company"}),
            await client.get("/api/companies/1/yandex-auth-url"),
            await client.delete("/api/companies/1"),
        ]

    for response in responses:
        assert response.status_code in (401, 403, 307, 303)


@pytest.mark.asyncio
async def test_projects_api_endpoints_require_auth():
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        responses = [
            await client.get("/api/projects"),
            await client.get("/api/projects/1"),
            await client.get("/api/projects/by-company/1"),
            await client.get("/api/projects/by-company-no-auth/1"),
            await client.post("/api/projects", json={"name": "Demo", "company_id": 1}),
            await client.get("/api/companies/1/projects"),
        ]

    for response in responses:
        assert response.status_code in (401, 403, 307, 303)
