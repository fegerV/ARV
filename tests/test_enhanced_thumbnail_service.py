import importlib
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from PIL import Image


def test_thumbnail_config_file_extension_and_cache_key():
    service_module = _enhanced_thumbnail_module()
    service = service_module.EnhancedThumbnailService()
    config = service_module.ThumbnailConfig(
        service_module.ThumbnailSize.SMALL,
        service_module.ThumbnailFormat.WEBP,
    )

    assert config.file_extension == ".webp"
    assert service.get_cache_key("abc123", config) == "thumb:small:webp:abc123"


@pytest.mark.asyncio
async def test_get_file_hash_and_validate_image_file_success(monkeypatch):
    service_module = _enhanced_thumbnail_module()
    service = service_module.EnhancedThumbnailService()
    temp_dir = _make_temp_dir()
    image_path = temp_dir / "image.png"
    _create_image(image_path, mode="RGBA", size=(320, 240))

    file_hash = await service.get_file_hash(str(image_path))
    validation = await service.validate_image_file(str(image_path))

    assert len(file_hash) == 64
    assert validation.is_valid is True
    assert validation.file_hash == file_hash
    assert validation.metadata["format"] == "PNG"
    assert validation.metadata["has_transparency"] is True


@pytest.mark.asyncio
async def test_get_file_hash_and_validate_image_file_cover_error_and_exif(monkeypatch):
    service_module = _enhanced_thumbnail_module()
    service = service_module.EnhancedThumbnailService()
    temp_dir = _make_temp_dir()
    image_path = temp_dir / "photo.jpg"

    exif = Image.Exif()
    exif[270] = "thumbnail metadata"
    Image.new("RGB", (64, 64), (10, 20, 30)).save(image_path, format="JPEG", exif=exif)

    validation = await service.validate_image_file(str(image_path))

    assert validation.is_valid is True
    assert validation.metadata["format"] == "JPEG"
    assert validation.metadata["exif"][270] == "thumbnail metadata"

    def _raise_open(*args, **kwargs):
        raise OSError("cannot open")

    monkeypatch.setattr(service_module, "open", _raise_open, raising=False)

    with pytest.raises(OSError, match="cannot open"):
        await service.get_file_hash(str(image_path))


@pytest.mark.asyncio
async def test_validate_image_file_handles_missing_large_and_invalid_images():
    service_module = _enhanced_thumbnail_module()
    service = service_module.EnhancedThumbnailService()
    temp_dir = _make_temp_dir()
    missing = await service.validate_image_file(str(temp_dir / "missing.png"))

    large_path = temp_dir / "large.png"
    _create_image(large_path, mode="RGB", size=(10, 10))
    service.max_file_size = 1
    too_large = await service.validate_image_file(str(large_path))

    invalid_path = temp_dir / "broken.txt"
    invalid_path.write_text("not an image", encoding="utf-8")
    service.max_file_size = 50 * 1024 * 1024
    invalid = await service.validate_image_file(str(invalid_path))

    assert missing.is_valid is False
    assert missing.error_message == "File does not exist"
    assert too_large.is_valid is False
    assert "File too large" in too_large.error_message
    assert invalid.is_valid is False
    assert "Image validation failed" in invalid.error_message


@pytest.mark.asyncio
async def test_get_cached_thumbnail_and_cache_thumbnail(monkeypatch):
    service_module = _enhanced_thumbnail_module()
    service = service_module.EnhancedThumbnailService()
    redis = _FakeRedis()
    monkeypatch.setattr(service_module, "redis_client", redis)
    config = service_module.ThumbnailConfig(
        service_module.ThumbnailSize.MEDIUM,
        service_module.ThumbnailFormat.WEBP,
    )
    result = service_module.ThumbnailResult(
        status="ready",
        thumbnail_path="/tmp/thumb.webp",
        thumbnail_url="/storage/thumb.webp",
        file_size=123,
        config=config,
    )

    await service.cache_thumbnail("hash123", config, result)
    cached = await service.get_cached_thumbnail("hash123", config)

    assert redis.last_setex[0] == "thumb:medium:webp:hash123"
    assert cached.status == "ready"
    assert cached.thumbnail_path == "/tmp/thumb.webp"
    assert cached.thumbnail_url == "/storage/thumb.webp"
    assert cached.file_size == 123
    assert cached.cache_hit is True


@pytest.mark.asyncio
async def test_get_cached_thumbnail_and_cache_thumbnail_swallow_redis_errors(monkeypatch):
    service_module = _enhanced_thumbnail_module()
    service = service_module.EnhancedThumbnailService()
    monkeypatch.setattr(service_module, "redis_client", _FakeRedis(fail_get=True, fail_setex=True))
    config = service_module.ThumbnailConfig(
        service_module.ThumbnailSize.MEDIUM,
        service_module.ThumbnailFormat.WEBP,
    )

    cached = await service.get_cached_thumbnail("hash123", config)
    await service.cache_thumbnail("hash123", config, service_module.ThumbnailResult(status="ready"))

    assert cached is None


@pytest.mark.asyncio
async def test_generate_thumbnail_returns_cached_result(monkeypatch):
    service_module = _enhanced_thumbnail_module()
    service = service_module.EnhancedThumbnailService()
    config = service_module.ThumbnailConfig(
        service_module.ThumbnailSize.MEDIUM,
        service_module.ThumbnailFormat.WEBP,
    )
    cached_result = service_module.ThumbnailResult(status="ready", cache_hit=True, config=config)

    monkeypatch.setattr(service, "validate_image_file", _async_return(SimpleNamespace(is_valid=True, file_hash="hash123", metadata={})))
    monkeypatch.setattr(service, "get_cached_thumbnail", _async_return(cached_result))

    result = await service.generate_thumbnail("source.png", config=config)

    assert result is cached_result


@pytest.mark.asyncio
async def test_generate_thumbnail_local_and_cloud_paths(monkeypatch):
    service_module = _enhanced_thumbnail_module()
    service = service_module.EnhancedThumbnailService()
    temp_dir = _make_temp_dir()
    media_root = temp_dir / "media-root"
    config = service_module.ThumbnailConfig(
        service_module.ThumbnailSize.LARGE,
        service_module.ThumbnailFormat.WEBP,
    )

    monkeypatch.setattr(service_module, "settings", SimpleNamespace(MEDIA_ROOT=str(media_root)))
    monkeypatch.setattr(service, "validate_image_file", _async_return(SimpleNamespace(is_valid=True, file_hash="hash123", metadata={})))
    monkeypatch.setattr(service, "get_cached_thumbnail", _async_return(None))
    monkeypatch.setattr(service, "_generate_thumbnail_in_memory", _async_return(b"thumb-bytes"))
    monkeypatch.setattr(service, "cache_thumbnail", _async_return(None))

    local = await service.generate_thumbnail("source.png", config=config)

    assert local.status == "ready"
    assert local.thumbnail_path.endswith("source_large.webp")
    assert local.thumbnail_url.endswith("/source_large.webp")
    assert Path(local.thumbnail_path).exists()
    assert local.file_size == len(b"thumb-bytes")

    monkeypatch.setattr(service, "_save_to_cloud_storage", _async_return("https://cdn.example.com/thumb.webp"))
    cloud = await service.generate_thumbnail("source.png", config=config, provider=SimpleNamespace(), company_id=9, force_regenerate=True)

    assert cloud.status == "ready"
    assert cloud.thumbnail_path == "thumbnails/9/source_large.webp"
    assert cloud.thumbnail_url == "https://cdn.example.com/thumb.webp"


@pytest.mark.asyncio
async def test_generate_thumbnail_uses_default_config(monkeypatch):
    service_module = _enhanced_thumbnail_module()
    service = service_module.EnhancedThumbnailService()
    temp_dir = _make_temp_dir()
    media_root = temp_dir / "media-root"

    monkeypatch.setattr(service_module, "settings", SimpleNamespace(MEDIA_ROOT=str(media_root)))
    monkeypatch.setattr(service, "validate_image_file", _async_return(SimpleNamespace(is_valid=True, file_hash="hash123", metadata={})))
    monkeypatch.setattr(service, "get_cached_thumbnail", _async_return(None))
    monkeypatch.setattr(service, "_generate_thumbnail_in_memory", _async_return(b"default-bytes"))
    monkeypatch.setattr(service, "cache_thumbnail", _async_return(None))

    result = await service.generate_thumbnail("source.png")

    assert result.status == "ready"
    assert result.config == service.default_configs[1]
    assert result.thumbnail_path.endswith("source_medium.webp")


@pytest.mark.asyncio
async def test_generate_thumbnail_handles_validation_failure_and_generation_error(monkeypatch):
    service_module = _enhanced_thumbnail_module()
    service = service_module.EnhancedThumbnailService()
    config = service_module.ThumbnailConfig(
        service_module.ThumbnailSize.MEDIUM,
        service_module.ThumbnailFormat.WEBP,
    )

    monkeypatch.setattr(service, "validate_image_file", _async_return(SimpleNamespace(is_valid=False)))
    invalid = await service.generate_thumbnail("source.png", config=config)

    monkeypatch.setattr(service, "validate_image_file", _async_return(SimpleNamespace(is_valid=True, file_hash="hash123", metadata={})))
    monkeypatch.setattr(service, "get_cached_thumbnail", _async_return(None))
    monkeypatch.setattr(service, "_generate_thumbnail_in_memory", _async_raise(RuntimeError("boom")))
    failed = await service.generate_thumbnail("source.png", config=config)

    assert invalid.status == "failed"
    assert failed.status == "failed"


@pytest.mark.asyncio
async def test_generate_thumbnail_in_memory_handles_formats():
    service_module = _enhanced_thumbnail_module()
    service = service_module.EnhancedThumbnailService()
    temp_dir = _make_temp_dir()
    rgba_path = temp_dir / "rgba.png"
    palette_path = temp_dir / "palette.gif"
    _create_image(rgba_path, mode="RGBA", size=(800, 600))
    Image.new("P", (800, 600)).save(palette_path, format="GIF")

    jpeg_config = service_module.ThumbnailConfig(
        service_module.ThumbnailSize.SMALL,
        service_module.ThumbnailFormat.JPEG,
    )
    png_config = service_module.ThumbnailConfig(
        service_module.ThumbnailSize.SMALL,
        service_module.ThumbnailFormat.PNG,
    )

    jpeg_data = await service._generate_thumbnail_in_memory(str(rgba_path), jpeg_config, {})
    png_data = await service._generate_thumbnail_in_memory(str(palette_path), png_config, {})

    assert jpeg_data.startswith(b"\xff\xd8")
    assert png_data.startswith(b"\x89PNG")


@pytest.mark.asyncio
async def test_generate_thumbnail_in_memory_covers_palette_and_la_conversion():
    service_module = _enhanced_thumbnail_module()
    service = service_module.EnhancedThumbnailService()
    temp_dir = _make_temp_dir()
    palette_path = temp_dir / "palette.gif"
    la_path = temp_dir / "gray-alpha.png"
    Image.new("P", (400, 300)).save(palette_path, format="GIF")
    Image.new("LA", (400, 300), (200, 120)).save(la_path, format="PNG")

    jpeg_config = service_module.ThumbnailConfig(
        service_module.ThumbnailSize.SMALL,
        service_module.ThumbnailFormat.JPEG,
    )
    webp_config = service_module.ThumbnailConfig(
        service_module.ThumbnailSize.SMALL,
        service_module.ThumbnailFormat.WEBP,
    )

    jpeg_data = await service._generate_thumbnail_in_memory(str(palette_path), jpeg_config, {})
    webp_data = await service._generate_thumbnail_in_memory(str(la_path), webp_config, {})

    assert jpeg_data.startswith(b"\xff\xd8")
    assert webp_data[:4] == b"RIFF"


@pytest.mark.asyncio
async def test_save_to_cloud_storage_uploads_and_cleans_temp_file():
    service_module = _enhanced_thumbnail_module()
    service = service_module.EnhancedThumbnailService()
    seen = {}
    config = service_module.ThumbnailConfig(
        service_module.ThumbnailSize.SMALL,
        service_module.ThumbnailFormat.WEBP,
    )

    class FakeProvider:
        async def upload_file(self, file_path, storage_path, content_type):
            seen["file_path"] = file_path
            seen["storage_path"] = storage_path
            seen["content_type"] = content_type
            seen["exists_during_upload"] = Path(file_path).exists()
            return "https://cdn.example.com/thumb.webp"

    result = await service._save_to_cloud_storage(
        b"thumb-data",
        FakeProvider(),
        "thumbnails/demo.webp",
        config,
    )

    assert result == "https://cdn.example.com/thumb.webp"
    assert seen["storage_path"] == "thumbnails/demo.webp"
    assert seen["content_type"] == "image/webp"
    assert seen["exists_during_upload"] is True
    assert Path(seen["file_path"]).exists() is False


@pytest.mark.asyncio
async def test_generate_multiple_thumbnails_and_info_and_clear_cache(monkeypatch):
    service_module = _enhanced_thumbnail_module()
    service = service_module.EnhancedThumbnailService()
    temp_dir = _make_temp_dir()
    source = temp_dir / "source.png"
    _create_image(source, mode="RGB", size=(320, 240))
    redis = _FakeRedis()
    monkeypatch.setattr(service_module, "redis_client", redis)

    configs = [
        service_module.ThumbnailConfig(service_module.ThumbnailSize.SMALL, service_module.ThumbnailFormat.WEBP),
        service_module.ThumbnailConfig(service_module.ThumbnailSize.MEDIUM, service_module.ThumbnailFormat.WEBP),
    ]

    async def _fake_generate(*, file_path, config, provider, company_id, force_regenerate):
        if config.size == service_module.ThumbnailSize.SMALL:
            return service_module.ThumbnailResult(status="ready", config=config)
        raise RuntimeError("generation failed")

    monkeypatch.setattr(service, "generate_thumbnail", _fake_generate)
    results = await service.generate_multiple_thumbnails(str(source), configs=configs)

    assert results[0].status == "ready"
    assert results[1].status == "failed"
    assert results[1].error_message == "generation failed"

    file_hash = await service.get_file_hash(str(source))
    for config in service.default_configs:
        redis.store[service.get_cache_key(file_hash, config)] = json.dumps({"cached": True})

    info = await service.get_thumbnail_info(str(source))
    deleted_file_keys = await service.clear_cache(str(source))
    redis.store["thumb:extra"] = "1"
    deleted_all = await service.clear_cache()

    assert info["file_hash"] == file_hash
    assert len(info["available_thumbnails"]) == len(service.default_configs)
    assert all(item["cached"] is True for item in info["available_thumbnails"])
    assert deleted_file_keys == len(service.default_configs)
    assert deleted_all == 1


@pytest.mark.asyncio
async def test_generate_multiple_thumbnails_uses_default_configs_and_clear_cache_empty(monkeypatch):
    service_module = _enhanced_thumbnail_module()
    service = service_module.EnhancedThumbnailService()
    monkeypatch.setattr(service_module, "redis_client", _FakeRedis())

    async def _fake_generate(*, file_path, config, provider, company_id, force_regenerate):
        return service_module.ThumbnailResult(status="ready", config=config)

    monkeypatch.setattr(service, "generate_thumbnail", _fake_generate)

    results = await service.generate_multiple_thumbnails("source.png")
    deleted = await service.clear_cache()

    assert len(results) == len(service.default_configs)
    assert all(result.config in service.default_configs for result in results)
    assert deleted == 0


@pytest.mark.asyncio
async def test_get_thumbnail_info_and_clear_cache_swallow_errors(monkeypatch):
    service_module = _enhanced_thumbnail_module()
    service = service_module.EnhancedThumbnailService()
    monkeypatch.setattr(service, "get_file_hash", _async_raise(RuntimeError("hash boom")))
    monkeypatch.setattr(service_module, "redis_client", _FakeRedis(fail_delete=True))

    info = await service.get_thumbnail_info("source.png")
    deleted = await service.clear_cache("source.png")

    assert info == {"error": "hash boom"}
    assert deleted == 0


class _FakeRedis:
    def __init__(self, fail_get=False, fail_setex=False, fail_delete=False):
        self.store = {}
        self.fail_get = fail_get
        self.fail_setex = fail_setex
        self.fail_delete = fail_delete
        self.last_setex = None

    async def get(self, key):
        if self.fail_get:
            raise RuntimeError("redis get failed")
        return self.store.get(key)

    async def setex(self, key, ttl, value):
        if self.fail_setex:
            raise RuntimeError("redis set failed")
        self.last_setex = (key, ttl, value)
        self.store[key] = value

    async def exists(self, key):
        return 1 if key in self.store else 0

    async def delete(self, *keys):
        if self.fail_delete:
            raise RuntimeError("redis delete failed")
        deleted = 0
        for key in keys:
            if key in self.store:
                deleted += 1
                del self.store[key]
        return deleted

    async def keys(self, pattern):
        if pattern == "thumb:*":
            return [key for key in self.store if key.startswith("thumb:")]
        return []


def _enhanced_thumbnail_module():
    return importlib.import_module("app.services.enhanced_thumbnail_service")


def _make_temp_dir() -> Path:
    root = Path("e:/Project/ARV/.pytest-temp") / f"enhanced-thumb-{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _create_image(path: Path, mode: str, size: tuple[int, int]):
    image = Image.new(mode, size, (255, 0, 0, 128) if "A" in mode else (255, 0, 0))
    image.save(path)


def _async_return(value):
    async def _inner(*args, **kwargs):
        return value

    return _inner


def _async_raise(exc):
    async def _inner(*args, **kwargs):
        raise exc

    return _inner
