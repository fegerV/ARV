import importlib
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_generate_thumbnail_cached_generated_and_failure(monkeypatch):
    mod = _module()

    request = mod.ThumbnailRequest(file_path="photo.png")
    cache_calls = []

    async def _cache_get(key, cache_type):
        cache_calls.append((key, cache_type))
        return {"thumbnail_url": "/cached.webp"}

    monkeypatch.setattr(mod, "enhanced_cache_service", SimpleNamespace(get=_cache_get, set=_async_return(True)))
    cached = await mod.generate_thumbnail(request, _bg())
    assert cached["status"] == "cached"
    assert cached["result"]["thumbnail_url"] == "/cached.webp"
    assert cache_calls[0][1] == "thumbnails"

    async def _thumb_generate(**kwargs):
        return SimpleNamespace(
            status="ready",
            thumbnail_url="/thumb.webp",
            thumbnail_path="thumb.webp",
            file_size=123,
            generation_time=0.5,
            cache_hit=False,
        )

    saved = {}

    async def _cache_set(key, value, cache_type, ttl=None):
        saved["cache_type"] = cache_type
        saved["ttl"] = ttl
        saved["value"] = value
        return True

    monkeypatch.setattr(
        mod,
        "enhanced_cache_service",
        SimpleNamespace(get=_async_return(None), set=_cache_set),
    )
    monkeypatch.setattr(mod, "enhanced_thumbnail_service", SimpleNamespace(generate_thumbnail=_thumb_generate))

    generated = await mod.generate_thumbnail(
        mod.ThumbnailRequest(file_path="photo.png", size="small", format="png", quality=77),
        _bg(),
    )

    assert generated["status"] == "ready"
    assert generated["config"]["size"] == "small"
    assert generated["config"]["format"] == "png"
    assert saved["cache_type"] == "thumbnails"
    assert saved["ttl"] == 3600

    monkeypatch.setattr(
        mod,
        "enhanced_thumbnail_service",
        SimpleNamespace(generate_thumbnail=_async_raise(RuntimeError("boom"))),
    )
    with pytest.raises(HTTPException) as exc:
        await mod.generate_thumbnail(request, _bg())
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_generate_batch_thumbnails_success_partial_failure_and_outer_failure(monkeypatch):
    mod = _module()
    request = mod.BatchThumbnailRequest(file_paths=["a.png", "b.png"], sizes=["small"], formats=["webp"])

    async def _generate_multiple(file_path, configs, force_regenerate):
        if file_path == "b.png":
            raise RuntimeError("bad file")
        return [
            SimpleNamespace(
                status="ready",
                config=SimpleNamespace(size=SimpleNamespace(size_name="small"), format=SimpleNamespace(value="webp")),
                thumbnail_url="/a-small.webp",
                thumbnail_path="a-small.webp",
                file_size=42,
                generation_time=0.1,
            )
        ]

    monkeypatch.setattr(mod, "enhanced_thumbnail_service", SimpleNamespace(generate_multiple_thumbnails=_generate_multiple))
    result = await mod.generate_batch_thumbnails(request, _bg())
    assert result[0]["thumbnails"][0]["url"] == "/a-small.webp"
    assert result[1]["error"] == "bad file"

    monkeypatch.setattr(mod, "ThumbnailSize", _broken_enum())
    with pytest.raises(HTTPException) as exc:
        await mod.generate_batch_thumbnails(request, _bg())
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_validate_file_cached_generated_and_failure(monkeypatch):
    mod = _module()
    request = mod.ValidationRequest(file_path="media.bin", validation_level="paranoid")

    monkeypatch.setattr(
        mod,
        "enhanced_cache_service",
        SimpleNamespace(get=_async_return({"is_valid": True}), set=_async_return(True)),
    )
    cached = await mod.validate_file(request)
    assert cached["status"] == "cached"

    validation_result = SimpleNamespace(
        is_valid=False,
        threat_level=SimpleNamespace(value="suspicious"),
        errors=["e1"],
        warnings=["w1"],
        metadata={"m": 1},
        security_info={"s": 2},
        file_info={"f": 3},
        validation_time=1.2,
        validation_level=SimpleNamespace(value="paranoid"),
    )
    stored = {}

    async def _cache_set(key, value, cache_type, ttl=None):
        stored["cache_type"] = cache_type
        stored["ttl"] = ttl
        return True

    monkeypatch.setattr(
        mod,
        "enhanced_cache_service",
        SimpleNamespace(get=_async_return(None), set=_cache_set),
    )
    monkeypatch.setattr(mod, "enhanced_validation_service", SimpleNamespace(validate_file=_async_return(validation_result)))
    generated = await mod.validate_file(request)

    assert generated["is_valid"] is False
    assert generated["threat_level"] == "suspicious"
    assert stored["cache_type"] == "validation"
    assert stored["ttl"] == 300

    monkeypatch.setattr(
        mod,
        "enhanced_validation_service",
        SimpleNamespace(validate_file=_async_raise(RuntimeError("bad validate"))),
    )
    with pytest.raises(HTTPException):
        await mod.validate_file(request)


@pytest.mark.asyncio
async def test_validate_batch_files_and_failure(monkeypatch):
    mod = _module()
    request = mod.BatchValidationRequest(file_paths=["a", "b"], validation_level="standard")
    results = [
        SimpleNamespace(
            is_valid=True,
            threat_level=SimpleNamespace(value="safe"),
            errors=[],
            warnings=[],
            metadata={},
            security_info={},
            file_info={},
            validation_time=0.1,
            validation_level=SimpleNamespace(value="standard"),
        ),
        SimpleNamespace(
            is_valid=False,
            threat_level=SimpleNamespace(value="malicious"),
            errors=["err"],
            warnings=["warn"],
            metadata={"x": 1},
            security_info={"y": 2},
            file_info={"z": 3},
            validation_time=0.2,
            validation_level=SimpleNamespace(value="standard"),
        ),
    ]
    monkeypatch.setattr(mod, "enhanced_validation_service", SimpleNamespace(batch_validate=_async_return(results)))
    payload = await mod.validate_batch_files(request)
    assert payload[0]["file_path"] == "a"
    assert payload[1]["threat_level"] == "malicious"

    monkeypatch.setattr(mod, "enhanced_validation_service", SimpleNamespace(batch_validate=_async_raise(RuntimeError("kaput"))))
    with pytest.raises(HTTPException):
        await mod.validate_batch_files(request)


@pytest.mark.asyncio
async def test_get_media_info_clear_cache_stats_and_health(monkeypatch):
    mod = _module()

    monkeypatch.setattr(mod, "enhanced_thumbnail_service", SimpleNamespace(get_thumbnail_info=_async_return({"sizes": ["small"]})))
    monkeypatch.setattr(
        mod,
        "enhanced_validation_service",
        SimpleNamespace(
            validate_file=_async_return(
                SimpleNamespace(
                    is_valid=True,
                    threat_level=SimpleNamespace(value="safe"),
                    errors=[],
                    warnings=[],
                    metadata={"format": "png"},
                )
            )
        ),
    )
    monkeypatch.setattr(
        mod,
        "enhanced_cache_service",
        SimpleNamespace(
            get_stats=lambda: {"l1_stats": {"entries": 1}, "l3_stats": {"files": 2}},
            invalidate_pattern=_async_return(3),
            clear_all=_async_return(None),
        ),
    )
    monkeypatch.setattr(
        mod,
        "reliability_service",
        SimpleNamespace(
            health_checker=SimpleNamespace(get_overall_health=_async_return({
                "status": "ok",
                "message": "healthy",
                "checks": {"cache": "ok"},
                "timestamp": "2026-03-30T00:00:00",
            })),
            get_reliability_stats=_async_return({"cb": "ok"}),
        ),
    )

    info = await mod.get_media_info("file.png")
    assert info.file_path == "file.png"
    assert info.cache_status["cache_available"] is True

    cleared_pattern = await mod.clear_cache(pattern="thumb:*", cache_type="thumbnails")
    cleared_all = await mod.clear_cache()
    stats = await mod.get_cache_stats()
    health = await mod.get_system_health()

    assert cleared_pattern["deleted_count"] == 3
    assert cleared_all["message"] == "All cache cleared"
    assert stats["l3_stats"]["files"] == 2
    assert health.status == "ok"

    monkeypatch.setattr(mod, "enhanced_cache_service", SimpleNamespace(get_stats=_raise_sync(RuntimeError("stats fail"))))
    with pytest.raises(HTTPException):
        await mod.get_cache_stats()


@pytest.mark.asyncio
async def test_generate_ar_content_thumbnails_invalid_not_found_no_files_and_success(monkeypatch):
    mod = _module()

    db_invalid = _FakeDb()
    with pytest.raises(HTTPException) as invalid:
        await mod.generate_ar_content_thumbnails("not-a-uuid", _bg(), db_invalid)
    assert invalid.value.status_code == 400
    assert db_invalid.rolled_back is True

    db_missing = _FakeDb(ar_content=None)
    with pytest.raises(HTTPException) as missing:
        await mod.generate_ar_content_thumbnails(str(uuid4()), _bg(), db_missing)
    assert missing.value.status_code == 404
    assert db_missing.rolled_back is True

    ar_content = SimpleNamespace(id=1, unique_id=str(uuid4()), company_id=9, photo_path=None, thumbnail_url=None)
    db_no_files = _FakeDb(ar_content=ar_content, videos=[])
    no_files = await mod.generate_ar_content_thumbnails(ar_content.unique_id, _bg(), db_no_files)
    assert no_files["status"] == "no_files"

    ar_content.photo_path = "photo.png"
    video = SimpleNamespace(id=7, video_path="video.mp4", thumbnail_url=None, preview_url=None)
    db_success = _FakeDb(ar_content=ar_content, videos=[video])

    async def _generate_multiple(file_path, configs, company_id=None):
        if file_path == "photo.png":
            return [
                SimpleNamespace(
                    status="ready",
                    config=SimpleNamespace(size=mod.ThumbnailSize.MEDIUM, format=SimpleNamespace(value="webp")),
                    thumbnail_url="/photo-medium.webp",
                    thumbnail_path="photo-medium.webp",
                )
            ]
        return [
            SimpleNamespace(
                status="ready",
                config=SimpleNamespace(size=mod.ThumbnailSize.SMALL, format=SimpleNamespace(value="webp")),
                thumbnail_url="/video-small.webp",
                thumbnail_path="video-small.webp",
            ),
            SimpleNamespace(
                status="ready",
                config=SimpleNamespace(size=mod.ThumbnailSize.MEDIUM, format=SimpleNamespace(value="webp")),
                thumbnail_url="/video-medium.webp",
                thumbnail_path="video-medium.webp",
            ),
        ]

    monkeypatch.setattr(mod, "enhanced_thumbnail_service", SimpleNamespace(generate_multiple_thumbnails=_generate_multiple))
    success = await mod.generate_ar_content_thumbnails(ar_content.unique_id, _bg(), db_success)

    assert success["status"] == "completed"
    assert success["successful_files"] == 2
    assert ar_content.thumbnail_url == "/photo-medium.webp"
    assert video.preview_url == "/video-small.webp"
    assert video.thumbnail_url == "/video-medium.webp"
    assert db_success.committed is True


@pytest.mark.asyncio
async def test_generate_ar_content_thumbnails_handles_processing_failure_and_stats(monkeypatch):
    mod = _module()
    content_id = str(uuid4())
    ar_content = SimpleNamespace(id=2, unique_id=content_id, company_id=4, photo_path="photo.png", thumbnail_url=None)
    video = SimpleNamespace(id=8, video_path="video.mp4", thumbnail_url=None, preview_url=None)
    db = _FakeDb(ar_content=ar_content, videos=[video], scalar_values=[5, 6])

    async def _generate_multiple(file_path, configs, company_id=None):
        if file_path == "photo.png":
            raise RuntimeError("thumb fail")
        return [
            SimpleNamespace(
                status="ready",
                config=SimpleNamespace(size=mod.ThumbnailSize.MEDIUM, format=SimpleNamespace(value="webp")),
                thumbnail_url="/video-medium.webp",
                thumbnail_path="video-medium.webp",
            )
        ]

    monkeypatch.setattr(mod, "enhanced_thumbnail_service", SimpleNamespace(generate_multiple_thumbnails=_generate_multiple))
    monkeypatch.setattr(mod, "enhanced_cache_service", SimpleNamespace(get_stats=lambda: {"cache": "ok"}))
    monkeypatch.setattr(mod, "reliability_service", SimpleNamespace(get_reliability_stats=_async_return({"retries": 1})))
    monkeypatch.setattr(mod, "time", SimpleNamespace(time=lambda: mod.start_time + 10))

    payload = await mod.generate_ar_content_thumbnails(content_id, _bg(), db)
    stats = await mod.get_media_stats(db)

    assert payload["processed_files"] == 2
    assert payload["successful_files"] == 1
    assert payload["results"][0]["status"] == "failed"
    assert stats["database"]["ar_content_count"] == 5
    assert stats["database"]["video_count"] == 6
    assert stats["system"]["uptime"] == 10

    broken_db = _FakeDb(scalar_error=RuntimeError("db fail"))
    with pytest.raises(HTTPException):
        await mod.get_media_stats(broken_db)


def _module():
    return importlib.import_module("app.api.routes.enhanced_media")


def _bg():
    return SimpleNamespace(add_task=lambda *args, **kwargs: None)


class _FakeScalarResult:
    def __init__(self, values):
        self._values = values

    def all(self):
        return self._values


class _FakeResult:
    def __init__(self, scalar_one=None, scalars_all=None):
        self._scalar_one = scalar_one
        self._scalars_all = scalars_all or []

    def scalar_one_or_none(self):
        return self._scalar_one

    def scalars(self):
        return _FakeScalarResult(self._scalars_all)


class _FakeDb:
    def __init__(self, ar_content=None, videos=None, scalar_values=None, scalar_error=None):
        self.ar_content = ar_content
        self.videos = videos or []
        self.scalar_values = list(scalar_values or [])
        self.scalar_error = scalar_error
        self.execute_calls = 0
        self.committed = False
        self.rolled_back = False

    async def execute(self, stmt):
        self.execute_calls += 1
        if self.execute_calls == 1:
            return _FakeResult(scalar_one=self.ar_content)
        return _FakeResult(scalars_all=self.videos)

    async def scalar(self, stmt):
        if self.scalar_error:
            raise self.scalar_error
        return self.scalar_values.pop(0)

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


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


def _broken_enum():
    class _Broken:
        def __class_getitem__(cls, key):
            raise ValueError("bad enum")

    return _Broken
