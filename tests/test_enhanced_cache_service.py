import importlib
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest


def test_disk_cache_default_path_and_module_import():
    service_module = _service_module()
    cache = service_module.DiskCache()

    assert cache.cache_dir.exists()
    assert cache.cache_dir.name == "vertex_cache"


@pytest.mark.asyncio
async def test_memory_cache_lru_delete_clear_and_stats():
    service_module = _service_module()
    cache = service_module.MemoryCache(max_size=120)

    assert await cache.get("missing") is None

    await cache.set("a", "x" * 40, ttl=10)
    await cache.set("b", "y" * 40, ttl=10)
    entry = await cache.get("a")

    assert entry.value == "x" * 40
    assert entry.access_count == 2
    assert cache.access_order[-1] == "a"

    await cache.set("c", "z" * 40, ttl=10)

    assert "b" not in cache.cache
    assert await cache.delete("a") is True
    assert await cache.delete("a") is False

    stats = cache.stats()
    assert stats["entries"] >= 1
    assert stats["size_bytes"] <= stats["max_size"]

    await cache.clear()
    assert cache.stats()["entries"] == 0


@pytest.mark.asyncio
async def test_disk_cache_get_set_delete_clear_and_corruption_handling():
    service_module = _service_module()
    cache = service_module.DiskCache(str(_make_temp_dir()))

    assert await cache.get("missing") is None
    assert await cache.set("alpha", {"value": "x" * 300}, ttl=30, compress=True) is True

    entry = await cache.get("alpha")
    assert entry.value["value"] == "x" * 300
    assert entry.cache_level == service_module.CacheLevel.L3_DISK

    path = cache._get_path("alpha")
    path.write_text("not-a-pickle", encoding="utf-8")
    assert await cache.get("alpha") is None
    assert path.exists() is False

    await cache.set("beta", {"value": 1}, compress=False)
    assert await cache.delete("beta") is True
    assert await cache.delete("beta") is False

    await cache.set("gamma", {"value": 2})
    await cache.clear()
    assert cache.stats()["files"] == 0


@pytest.mark.asyncio
async def test_disk_cache_expired_and_write_failure_paths(monkeypatch):
    service_module = _service_module()
    cache = service_module.DiskCache(str(_make_temp_dir()))

    await cache.set("alpha", {"value": "old"})
    path = cache._get_path("alpha")

    class _OldStat:
        st_mtime = 0
        st_size = 10

    monkeypatch.setattr(service_module.time, "time", lambda: 90000)
    monkeypatch.setattr(type(path), "stat", lambda self: _OldStat(), raising=False)

    assert await cache.get("alpha") is None
    assert path.exists() is False

    broken_dir = _make_temp_dir() / "missing-parent" / "nested"
    failing_cache = service_module.DiskCache(str(broken_dir))
    failing_cache.cache_dir = broken_dir / "does-not-exist"

    assert await failing_cache.set("broken", {"v": 1}) is False


@pytest.mark.asyncio
async def test_enhanced_cache_get_set_delete_and_get_or_set(monkeypatch):
    service_module = _service_module()
    service = _make_service(service_module)
    redis = _FakeRedis()
    disk = service_module.DiskCache(str(_make_temp_dir()))
    service.l2_cache = redis
    service.l3_cache = disk

    assert await service.set("thumb-1", {"name": "demo"}, cache_type="thumbnails") is True
    assert await service.get("thumb-1", cache_type="thumbnails") == {"name": "demo"}

    service.l1_cache.cache.clear()
    service.l1_cache.access_order.clear()
    l2_value = await service.get("thumb-1", cache_type="thumbnails", strategy=service_module.CacheStrategy.WRITE_THROUGH)
    assert l2_value == {"name": "demo"}
    assert "thumb-1" in service.l1_cache.cache

    await service.delete("thumb-1", cache_type="thumbnails")
    assert await service.get("thumb-1", cache_type="thumbnails") is None

    calls = []

    def factory():
        calls.append("sync")
        return {"value": 7}

    async def async_factory():
        calls.append("async")
        return {"value": 9}

    assert await service.get_or_set("meta-1", factory, cache_type="metadata") == {"value": 7}
    assert await service.get_or_set("meta-1", factory, cache_type="metadata") == {"value": 7}
    assert await service.get_or_set("meta-2", async_factory, cache_type="metadata") == {"value": 9}
    assert calls == ["sync", "async"]


@pytest.mark.asyncio
async def test_enhanced_cache_get_promotes_disk_and_handles_errors(monkeypatch):
    service_module = _service_module()
    service = _make_service(service_module)
    service.l2_cache = _FakeRedis(fail_get=True)

    disk_entry = service_module.CacheEntry(
        key="media-1",
        value={"value": "from-disk"},
        created_at=service_module.time.time(),
        accessed_at=service_module.time.time(),
        ttl=600,
    )

    async def _get_disk(key):
        return disk_entry

    service.l3_cache = SimpleNamespace(get=_get_disk, set=_async_return(True), delete=_async_return(True), stats=lambda: {"size_bytes": 0})

    value = await service.get("media-1", cache_type="media_info", strategy=service_module.CacheStrategy.WRITE_THROUGH)

    assert value == {"value": "from-disk"}
    assert "media-1" in service.l1_cache.cache

    expired_entry = service_module.CacheEntry(key="x", value=1, created_at=0, accessed_at=0, ttl=1)
    monkeypatch.setattr(service_module.time, "time", lambda: 10)
    assert service._is_expired(expired_entry) is True

    monkeypatch.setattr(service, "_get_config", _raise_sync(RuntimeError("config boom")))
    assert await service.get("broken") is None


@pytest.mark.asyncio
async def test_enhanced_cache_set_strategies_and_error_paths(monkeypatch):
    service_module = _service_module()
    service = _make_service(service_module)
    redis = _FakeRedis()
    service.l2_cache = redis
    service.l3_cache = SimpleNamespace(
        set=_async_return(True),
        get=_async_return(None),
        delete=_async_return(False),
        clear=_async_return(None),
        stats=lambda: {"size_bytes": 0},
    )

    tasks = []

    def _fake_create_task(coro):
        tasks.append(coro)
        coro.close()
        return "scheduled"

    monkeypatch.setattr(service_module.asyncio, "create_task", _fake_create_task)

    assert await service.set("lazy-key", {"v": 1}, cache_type="metadata", strategy=service_module.CacheStrategy.LAZY) is True
    assert redis.last_setex[0] == "lazy-key"

    assert await service.set("back-key", {"v": 2}, cache_type="thumbnails", strategy=service_module.CacheStrategy.WRITE_BACK) is True
    assert "back-key" in service.l1_cache.cache
    assert len(tasks) == 1

    monkeypatch.setattr(service, "_get_config", _raise_sync(RuntimeError("set boom")))
    assert await service.set("broken", {"v": 3}) is False


@pytest.mark.asyncio
async def test_delete_invalidate_pattern_warm_cache_and_clear_all(monkeypatch):
    service_module = _service_module()
    service = _make_service(service_module)
    redis = _FakeRedis()
    service.l2_cache = redis
    disk = service_module.DiskCache(str(_make_temp_dir()))
    service.l3_cache = disk

    await service.set("a:1", {"v": 1}, cache_type="thumbnails")
    await service.set("a:2", {"v": 2}, cache_type="metadata")
    redis.store["a:extra"] = json.dumps({"v": 3})

    deleted = await service.invalidate_pattern("a:*", cache_type="metadata")
    assert deleted >= 1

    warmed = await service.warm_cache(["w1", "w2"], lambda key: {"key": key}, cache_type="metadata")
    assert warmed == [{"key": "w1"}, {"key": "w2"}]

    stats_before = service.get_stats()
    assert "operations" in stats_before
    assert "configurations" in stats_before

    await service.clear_all()
    assert service.l1_cache.stats()["entries"] == 0
    assert redis.store == {}
    assert service.stats["hits"][service_module.CacheLevel.L1_MEMORY.value] == 0

    monkeypatch.setattr(service, "_get_config", _raise_sync(RuntimeError("delete boom")))
    assert await service.delete("x") is False
    assert await service.invalidate_pattern("x:*") == 0


@pytest.mark.asyncio
async def test_set_l2_background_write_hit_rate_and_cleanup(monkeypatch):
    service_module = _service_module()
    service = _make_service(service_module)
    redis = _FakeRedis()
    service.l2_cache = redis
    service.l3_cache = SimpleNamespace(
        set=_async_return(True),
        stats=lambda: {"size_bytes": 128},
        clear=_async_return(None),
    )

    json_config = service_module.CacheConfig(service_module.CacheLevel.L2_REDIS, ttl=10, serialization="json")
    pickle_config = service_module.CacheConfig(service_module.CacheLevel.L2_REDIS, ttl=0, serialization="pickle")

    await service._set_l2("json-key", {"v": 1}, json_config, ttl=5)
    assert redis.last_setex[0] == "json-key"

    await service._set_l2("pickle-key", {"v": 2}, pickle_config, ttl=0)
    assert "pickle-key" in redis.store

    redis.fail_set = True
    await service._set_l2("broken-key", {"v": 3}, json_config, ttl=5)

    redis.fail_set = False
    await service._background_write("bg-key", {"v": 4}, json_config)
    assert "bg-key" in redis.store

    service.stats["hits"][service_module.CacheLevel.L1_MEMORY.value] = 3
    service.stats["misses"][service_module.CacheLevel.L1_MEMORY.value] = 1
    assert service._calculate_hit_rate(service_module.CacheLevel.L1_MEMORY) == 0.75

    marker = {"count": 0}

    async def _stop_sleep(seconds):
        marker["count"] += 1
        if marker["count"] == 1:
            return None
        raise asyncio.CancelledError()

    monkeypatch.setattr(service_module.asyncio, "sleep", _stop_sleep)
    with pytest.raises(asyncio.CancelledError):
        await service._background_cleanup()


@pytest.mark.asyncio
async def test_background_write_and_clear_all_swallow_errors(monkeypatch):
    service_module = _service_module()
    service = _make_service(service_module)
    service.l2_cache = _FakeRedis(fail_keys=True)
    service.l3_cache = SimpleNamespace(
        set=_async_raise(RuntimeError("disk fail")),
        clear=_async_return(None),
        stats=lambda: {"size_bytes": 0},
    )

    config = service_module.CacheConfig(service_module.CacheLevel.L2_REDIS, ttl=10)
    await service._background_write("x", {"v": 1}, config)

    await service.clear_all()
    assert all(value == 0 for value in service.stats["hits"].values())


def _service_module():
    return importlib.import_module("app.services.enhanced_cache_service")


def _make_temp_dir() -> Path:
    root = Path("e:/Project/ARV/.pytest-temp") / f"enhanced-cache-{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _make_service(service_module):
    class _Loop:
        def create_task(self, coro):
            coro.close()
            return "cleanup-task"

    original = service_module.asyncio.get_running_loop
    service_module.asyncio.get_running_loop = lambda: _Loop()
    try:
        return service_module.EnhancedCacheService()
    finally:
        service_module.asyncio.get_running_loop = original


class _FakeRedis:
    def __init__(self, fail_get=False, fail_set=False, fail_keys=False):
        self.store = {}
        self.fail_get = fail_get
        self.fail_set = fail_set
        self.fail_keys = fail_keys
        self.last_setex = None

    async def get(self, key):
        if self.fail_get:
            raise RuntimeError("redis get failed")
        return self.store.get(key)

    async def setex(self, key, ttl, value):
        if self.fail_set:
            raise RuntimeError("redis setex failed")
        self.last_setex = (key, ttl, value)
        self.store[key] = value

    async def set(self, key, value):
        if self.fail_set:
            raise RuntimeError("redis set failed")
        self.store[key] = value

    async def delete(self, *keys):
        deleted = 0
        for key in keys:
            if key in self.store:
                deleted += 1
                del self.store[key]
        return deleted

    async def keys(self, pattern):
        if self.fail_keys:
            raise RuntimeError("redis keys failed")
        if pattern == "*":
            return list(self.store.keys())
        prefix = pattern.rstrip("*")
        return [key for key in self.store if key.startswith(prefix)]


def _async_return(value):
    async def _inner(*args, **kwargs):
        return value

    return _inner


def _async_raise(exc):
    async def _inner(*args, **kwargs):
        raise exc

    return _inner


def _raise_sync(exc):
    def _inner(*args, **kwargs):
        raise exc

    return _inner
