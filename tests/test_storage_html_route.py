from types import SimpleNamespace

import pytest

from app.html.routes import storage as storage_route


@pytest.mark.asyncio
async def test_get_storage_info_reuses_fresh_cache(monkeypatch):
    calls = {"count": 0}

    async def _fake_build(_db):
        calls["count"] += 1
        return {"companies": [{"name": "A"}], "used_storage": "1 B"}

    monkeypatch.setattr(storage_route, "_build_storage_info", _fake_build)
    monkeypatch.setattr(storage_route, "_STORAGE_INFO_CACHE", {"value": None, "timestamp": 0.0})
    monkeypatch.setattr(storage_route.time, "monotonic", lambda: 100.0)

    first = await storage_route.get_storage_info(SimpleNamespace())
    second = await storage_route.get_storage_info(SimpleNamespace())

    assert calls["count"] == 1
    assert first == second

    second["companies"][0]["name"] = "Mutated"
    assert storage_route._STORAGE_INFO_CACHE["value"]["companies"][0]["name"] == "A"


@pytest.mark.asyncio
async def test_get_storage_info_refreshes_after_ttl(monkeypatch):
    calls = {"count": 0}

    async def _fake_build(_db):
        calls["count"] += 1
        return {"companies": [], "used_storage": f"{calls['count']} B"}

    monotonic_values = [100.0, 161.0]

    def _fake_monotonic():
        if len(monotonic_values) > 1:
            return monotonic_values.pop(0)
        return monotonic_values[0]

    monkeypatch.setattr(storage_route, "_build_storage_info", _fake_build)
    monkeypatch.setattr(storage_route, "_STORAGE_INFO_CACHE", {"value": None, "timestamp": 0.0})
    monkeypatch.setattr(storage_route.time, "monotonic", _fake_monotonic)

    first = await storage_route.get_storage_info(SimpleNamespace())
    second = await storage_route.get_storage_info(SimpleNamespace())

    assert calls["count"] == 2
    assert first["used_storage"] == "1 B"
    assert second["used_storage"] == "2 B"
