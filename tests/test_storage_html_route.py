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
async def test_get_storage_info_returns_stale_cache_after_ttl(monkeypatch):
    calls = {"count": 0, "scheduled": 0}

    async def _fake_build(_db):
        calls["count"] += 1
        return {"companies": [], "used_storage": f"{calls['count']} B"}

    monotonic_values = [100.0, 161.0]

    def _fake_monotonic():
        if len(monotonic_values) > 1:
            return monotonic_values.pop(0)
        return monotonic_values[0]

    def _fake_schedule():
        calls["scheduled"] += 1

    monkeypatch.setattr(storage_route, "_build_storage_info", _fake_build)
    monkeypatch.setattr(storage_route, "_schedule_storage_info_refresh", _fake_schedule)
    monkeypatch.setattr(
        storage_route,
        "_STORAGE_INFO_CACHE",
        {"value": None, "timestamp": 0.0, "refresh_task": None},
    )
    monkeypatch.setattr(storage_route.time, "monotonic", _fake_monotonic)

    first = await storage_route.get_storage_info(SimpleNamespace())
    second = await storage_route.get_storage_info(SimpleNamespace())

    assert calls["count"] == 1
    assert calls["scheduled"] == 1
    assert first["used_storage"] == "1 B"
    assert second["used_storage"] == "1 B"


@pytest.mark.asyncio
async def test_get_storage_info_returns_stale_cache_and_schedules_refresh(monkeypatch):
    stale_value = {"companies": [{"name": "Cached"}], "used_storage": "1 B"}
    scheduled = {"called": 0}

    async def _fake_build(_db):
        raise AssertionError("stale path should not rebuild inline")

    def _fake_schedule():
        scheduled["called"] += 1

    monkeypatch.setattr(storage_route, "_build_storage_info", _fake_build)
    monkeypatch.setattr(storage_route, "_schedule_storage_info_refresh", _fake_schedule)
    monkeypatch.setattr(
        storage_route,
        "_STORAGE_INFO_CACHE",
        {"value": stale_value, "timestamp": 1.0, "refresh_task": None},
    )
    monkeypatch.setattr(storage_route.time, "monotonic", lambda: 100.0)

    result = await storage_route.get_storage_info(SimpleNamespace())

    assert result == stale_value
    assert scheduled["called"] == 1
