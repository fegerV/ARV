"""API tests. Smoke test ensures pytest collects tests (CI exit code 5 otherwise)."""

import pytest
from fastapi import FastAPI


def test_app_import():
    """Приложение импортируется и является экземпляром FastAPI."""
    from app.main import app
    assert isinstance(app, FastAPI)


@pytest.mark.asyncio
async def test_health_status_requires_super_admin():
    """Расширенный health-check закрыт для неаутентифицированных (ARV-018).

    Публичным остаётся только лёгкий ping-эндпоинт /api/health.
    """
    import httpx
    from app.main import app
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/health/status")
        assert response.status_code in (401, 403)

        ping = await client.get("/api/health")
        assert ping.status_code == 200
        assert ping.json() == {"status": "ok"}
