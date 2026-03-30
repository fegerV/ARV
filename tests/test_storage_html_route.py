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
async def test_get_yandex_folder_snapshot_reuses_fresh_cache(monkeypatch):
    provider = SimpleNamespace()
    monkeypatch.setattr(
        storage_route,
        "_YD_FOLDER_CACHE",
        {
            3: {
                "value": {"total_bytes": 123, "file_count": 4},
                "timestamp": 100.0,
                "refresh_task": None,
            }
        },
    )
    monkeypatch.setattr(storage_route.time, "monotonic", lambda: 120.0)

    snapshot = await storage_route._get_yandex_folder_snapshot(3, provider)

    assert snapshot == {"total_bytes": 123, "file_count": 4}
    snapshot["total_bytes"] = 999
    assert storage_route._YD_FOLDER_CACHE[3]["value"]["total_bytes"] == 123


@pytest.mark.asyncio
async def test_get_yandex_folder_snapshot_returns_stale_and_schedules_refresh(monkeypatch):
    provider = SimpleNamespace()
    scheduled = {"count": 0}

    def _fake_schedule(company_id, scheduled_provider):
        scheduled["count"] += 1
        assert company_id == 3
        assert scheduled_provider is provider

    monkeypatch.setattr(
        storage_route,
        "_YD_FOLDER_CACHE",
        {
            3: {
                "value": {"total_bytes": 321, "file_count": 7},
                "timestamp": 1.0,
                "refresh_task": None,
            }
        },
    )
    monkeypatch.setattr(storage_route.time, "monotonic", lambda: 1000.0)
    monkeypatch.setattr(storage_route, "_schedule_yandex_folder_cache_refresh", _fake_schedule)

    snapshot = await storage_route._get_yandex_folder_snapshot(3, provider)

    assert snapshot == {"total_bytes": 321, "file_count": 7}
    assert scheduled["count"] == 1


@pytest.mark.asyncio
async def test_get_yandex_folder_snapshot_cold_miss_schedules_refresh(monkeypatch):
    provider = SimpleNamespace()
    scheduled = {"count": 0}

    def _fake_schedule(company_id, scheduled_provider):
        scheduled["count"] += 1
        assert company_id == 4
        assert scheduled_provider is provider

    monkeypatch.setattr(storage_route, "_YD_FOLDER_CACHE", {})
    monkeypatch.setattr(storage_route.time, "monotonic", lambda: 1000.0)
    monkeypatch.setattr(storage_route, "_schedule_yandex_folder_cache_refresh", _fake_schedule)

    snapshot = await storage_route._get_yandex_folder_snapshot(4, provider)

    assert snapshot is None
    assert scheduled["count"] == 1


@pytest.mark.asyncio
async def test_refresh_yandex_folder_cache_updates_snapshot(monkeypatch):
    class _Provider:
        async def get_folder_size(self):
            return {"total_bytes": 555, "file_count": 9}

    monkeypatch.setattr(
        storage_route,
        "_YD_FOLDER_CACHE",
        {
            5: {
                "value": None,
                "timestamp": 0.0,
                "refresh_task": "pending",
            }
        },
    )
    monkeypatch.setattr(storage_route.time, "monotonic", lambda: 250.0)

    await storage_route._refresh_yandex_folder_cache(5, _Provider())

    assert storage_route._YD_FOLDER_CACHE[5]["value"] == {"total_bytes": 555, "file_count": 9}
    assert storage_route._YD_FOLDER_CACHE[5]["timestamp"] == 250.0
    assert storage_route._YD_FOLDER_CACHE[5]["refresh_task"] is None


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
