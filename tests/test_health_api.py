import httpx
import pytest


@pytest.mark.asyncio
async def test_health_ping_returns_ok():
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_status_reports_degraded_when_database_fails(monkeypatch):
    from app.api.routes import health

    class BrokenConnection:
        async def __aenter__(self):
            raise RuntimeError("db down")

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class BrokenEngine:
        def begin(self):
            return BrokenConnection()

    class Memory:
        percent = 42.0

    class Disk:
        percent = 73.5

    monkeypatch.setattr(health, "engine", BrokenEngine())
    monkeypatch.setattr(health.psutil, "cpu_percent", lambda interval=0.5: 12.5)
    monkeypatch.setattr(health.psutil, "virtual_memory", lambda: Memory())
    monkeypatch.setattr(health.psutil, "disk_usage", lambda path: Disk())

    result = await health.health_status()

    assert result["database"] == "unhealthy"
    assert result["database_error"] == "db down"
    assert result["system"] == {
        "cpu_percent": 12.5,
        "memory_percent": 42.0,
        "disk_percent": 73.5,
    }
    assert result["overall"] == "degraded"


@pytest.mark.asyncio
async def test_metrics_returns_204_when_prometheus_is_unavailable(monkeypatch):
    from app.api.routes import health

    monkeypatch.setattr(health, "generate_latest", None)
    monkeypatch.setattr(health, "CONTENT_TYPE_LATEST", "text/plain; version=0.0.4")

    response = await health.prometheus_metrics()

    assert response.status_code == 204
    assert response.media_type == "text/plain; version=0.0.4"
    assert response.body == b""
