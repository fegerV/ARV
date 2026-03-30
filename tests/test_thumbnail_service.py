import asyncio
import importlib
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from PIL import Image


@pytest.mark.asyncio
async def test_save_thumbnail_with_provider_uploads_and_cleans_temp_file():
    thumbnail_service = _thumbnail_service_module()
    service = thumbnail_service.ThumbnailService()
    uploaded = {}

    class FakeProvider:
        async def upload_file(self, file_path, remote_path, content_type):
            uploaded["file_path"] = file_path
            uploaded["remote_path"] = remote_path
            uploaded["content_type"] = content_type
            uploaded["exists_during_upload"] = Path(file_path).exists()
            return "https://cdn.example.com/thumb.webp"

    result = await service._save_thumbnail_with_provider(
        b"thumb-data",
        FakeProvider(),
        "thumbs/thumb.webp",
        "image/webp",
    )

    assert result == "https://cdn.example.com/thumb.webp"
    assert uploaded["remote_path"] == "thumbs/thumb.webp"
    assert uploaded["content_type"] == "image/webp"
    assert uploaded["exists_during_upload"] is True
    assert Path(uploaded["file_path"]).exists() is False


@pytest.mark.asyncio
async def test_save_thumbnail_with_provider_records_failure_and_cleans_temp_file():
    thumbnail_service = _thumbnail_service_module()
    service = thumbnail_service.ThumbnailService()
    uploaded = {}

    class FakeProvider:
        async def upload_file(self, file_path, remote_path, content_type):
            uploaded["file_path"] = file_path
            raise RuntimeError("upload failed")

    with pytest.raises(RuntimeError, match="upload failed"):
        await service._save_thumbnail_with_provider(
            b"thumb-data",
            FakeProvider(),
            "thumbs/thumb.webp",
            "image/webp",
        )

    assert Path(uploaded["file_path"]).exists() is False


@pytest.mark.asyncio
async def test_generate_image_thumbnail_creates_all_sizes_and_main_thumbnail(monkeypatch):
    thumbnail_service = _thumbnail_service_module()
    service = thumbnail_service.ThumbnailService()
    temp_dir = _make_temp_dir()
    image_path = temp_dir / "source.png"
    storage_path = temp_dir / "thumbs"
    _create_image(image_path, mode="RGBA", size=(640, 480))

    ar_content_utils = importlib.import_module("app.utils.ar_content")
    monkeypatch.setattr(ar_content_utils, "build_public_url", lambda path: f"/public/{Path(path).name}")

    result = await service.generate_image_thumbnail(
        image_path=str(image_path),
        storage_path=storage_path,
    )

    assert result["status"] == "ready"
    assert result["thumbnail_path"].endswith("thumbnail.webp")
    assert result["thumbnail_url"] == "/public/thumbnail.webp"
    assert set(result["thumbnails"].keys()) == {"small", "medium", "large"}
    assert (storage_path / "thumbnail_small.webp").exists()
    assert (storage_path / "thumbnail.webp").exists()
    assert (storage_path / "thumbnail_large.webp").exists()


@pytest.mark.asyncio
async def test_generate_image_thumbnail_handles_palette_and_non_rgb_modes(monkeypatch):
    thumbnail_service = _thumbnail_service_module()
    service = thumbnail_service.ThumbnailService()
    temp_dir = _make_temp_dir()
    palette_path = temp_dir / "palette.gif"
    cmyk_path = temp_dir / "cmyk.jpg"
    palette_storage = temp_dir / "palette-thumbs"
    cmyk_storage = temp_dir / "cmyk-thumbs"

    Image.new("P", (320, 240)).save(palette_path, format="GIF")
    Image.new("CMYK", (320, 240), (0, 128, 128, 0)).save(cmyk_path, format="JPEG")

    ar_content_utils = importlib.import_module("app.utils.ar_content")
    monkeypatch.setattr(ar_content_utils, "build_public_url", lambda path: f"/public/{Path(path).name}")

    palette_result = await service.generate_image_thumbnail(str(palette_path), palette_storage)
    cmyk_result = await service.generate_image_thumbnail(str(cmyk_path), cmyk_storage)

    assert palette_result["status"] == "ready"
    assert cmyk_result["status"] == "ready"
    assert (palette_storage / "thumbnail.webp").exists()
    assert (cmyk_storage / "thumbnail.webp").exists()


@pytest.mark.asyncio
async def test_generate_image_thumbnail_returns_failed_for_missing_storage_path():
    thumbnail_service = _thumbnail_service_module()
    service = thumbnail_service.ThumbnailService()

    result = await service.generate_image_thumbnail(
        image_path="missing.png",
        storage_path=None,
    )

    assert result["status"] == "failed"
    assert "storage_path is required" in result["error"]


@pytest.mark.asyncio
async def test_generate_image_thumbnail_returns_failed_when_main_thumbnail_missing(monkeypatch):
    thumbnail_service = _thumbnail_service_module()
    service = thumbnail_service.ThumbnailService()
    temp_dir = _make_temp_dir()
    image_path = temp_dir / "source.png"
    storage_path = temp_dir / "thumbs"
    _create_image(image_path, mode="RGB", size=(320, 240))

    ar_content_utils = importlib.import_module("app.utils.ar_content")
    monkeypatch.setattr(ar_content_utils, "build_public_url", lambda path: f"/public/{Path(path).name}")

    original_exists = Path.exists

    def _fake_exists(path_obj):
        if str(path_obj).endswith("thumbnail.webp"):
            return False
        return original_exists(path_obj)

    monkeypatch.setattr(Path, "exists", _fake_exists)

    result = await service.generate_image_thumbnail(
        image_path=str(image_path),
        storage_path=storage_path,
    )

    assert result["status"] == "failed"
    assert "Thumbnail file not created" in result["error"]


def test_derive_size_name_appends_suffix_before_extension():
    thumbnail_service = _thumbnail_service_module()
    service = thumbnail_service.ThumbnailService()

    assert service._derive_size_name("video_1_thumb.webp", "small") == "video_1_thumb_small.webp"


@pytest.mark.asyncio
async def test_extract_video_frame_success_and_failure_paths(monkeypatch):
    thumbnail_service = _thumbnail_service_module()
    service = thumbnail_service.ThumbnailService()
    temp_dir = _make_temp_dir()
    frame_path = temp_dir / "frame.png"
    frame_path.write_bytes(b"png")

    class FakeSuccessProcess:
        returncode = 0

        async def communicate(self):
            return b"", b""

    async def _fake_tempfile(*args, **kwargs):
        return None

    def _named_tempfile(*args, **kwargs):
        class _File:
            name = str(frame_path)

            def close(self):
                return None

        return _File()

    monkeypatch.setattr(thumbnail_service.tempfile, "NamedTemporaryFile", _named_tempfile)
    monkeypatch.setattr(thumbnail_service.asyncio, "create_subprocess_exec", _async_return(FakeSuccessProcess()))

    success = await service._extract_video_frame("video.mp4", 1.5)

    assert success == str(frame_path)

    class FakeFailProcess:
        returncode = 1

        async def communicate(self):
            return b"", b"ffmpeg error"

    monkeypatch.setattr(thumbnail_service.asyncio, "create_subprocess_exec", _async_return(FakeFailProcess()))

    with pytest.raises(RuntimeError, match="Video frame extraction failed: ffmpeg error"):
        await service._extract_video_frame("video.mp4", 1.5)

    frame_path.unlink(missing_ok=True)

    class FakeMissingProcess:
        returncode = 0

        async def communicate(self):
            return b"", b""

    monkeypatch.setattr(thumbnail_service.asyncio, "create_subprocess_exec", _async_return(FakeMissingProcess()))

    with pytest.raises(FileNotFoundError, match="Temp frame file not created"):
        await service._extract_video_frame("video.mp4", 1.5)


@pytest.mark.asyncio
async def test_generate_video_thumbnail_creates_local_webp_sizes(monkeypatch):
    thumbnail_service = _thumbnail_service_module()
    service = thumbnail_service.ThumbnailService()
    temp_dir = _make_temp_dir()
    output_dir = temp_dir / "video-thumbs"
    frame_path = temp_dir / "frame.png"
    _create_image(frame_path, mode="RGB", size=(800, 600))

    monkeypatch.setattr(service, "_extract_video_frame", _async_return(str(frame_path)))

    result = await service.generate_video_thumbnail(
        video_path="sample.mp4",
        output_dir=str(output_dir),
        thumbnail_name="sample_thumb.webp",
        time_position=2.0,
    )

    assert result["status"] == "ready"
    assert result["thumbnail_path"].endswith("sample_thumb_medium.webp")
    assert result["thumbnail_url"].endswith("/sample_thumb_medium.webp")
    assert set(result["thumbnails"].keys()) == {"small", "medium", "large"}
    assert (output_dir / "sample_thumb_small.webp").exists()
    assert (output_dir / "sample_thumb_medium.webp").exists()
    assert (output_dir / "sample_thumb_large.webp").exists()
    assert frame_path.exists() is False


@pytest.mark.asyncio
async def test_generate_video_thumbnail_handles_transparent_frame(monkeypatch):
    thumbnail_service = _thumbnail_service_module()
    service = thumbnail_service.ThumbnailService()
    temp_dir = _make_temp_dir()
    output_dir = temp_dir / "video-thumbs"
    frame_path = temp_dir / "frame.png"
    _create_image(frame_path, mode="RGBA", size=(800, 600))

    monkeypatch.setattr(service, "_extract_video_frame", _async_return(str(frame_path)))

    result = await service.generate_video_thumbnail(
        video_path="sample.mp4",
        output_dir=str(output_dir),
        thumbnail_name="sample_thumb.webp",
    )

    assert result["status"] == "ready"
    assert (output_dir / "sample_thumb_medium.webp").exists()
    assert frame_path.exists() is False


@pytest.mark.asyncio
async def test_generate_video_thumbnail_uses_provider_and_returns_failure_on_extract_error(monkeypatch):
    thumbnail_service = _thumbnail_service_module()
    service = thumbnail_service.ThumbnailService()
    temp_dir = _make_temp_dir()
    frame_path = temp_dir / "frame.png"
    _create_image(frame_path, mode="RGB", size=(800, 600))

    async def _fake_save(data, provider, remote_path, content_type):
        return f"https://cdn.example.com/{remote_path}"

    monkeypatch.setattr(service, "_extract_video_frame", _async_return(str(frame_path)))
    monkeypatch.setattr(service, "_save_thumbnail_with_provider", _fake_save)

    result = await service.generate_video_thumbnail(
        video_path="sample.mp4",
        thumbnail_name="sample_thumb.webp",
        provider=SimpleNamespace(),
        company_id=17,
    )

    assert result["status"] == "ready"
    assert result["thumbnail_path"] == "thumbnails/17/sample_thumb_medium.webp"
    assert result["thumbnail_url"] == "https://cdn.example.com/thumbnails/17/sample_thumb_medium.webp"
    assert frame_path.exists() is False

    monkeypatch.setattr(service, "_extract_video_frame", _async_raise(RuntimeError("ffmpeg boom")))

    failed = await service.generate_video_thumbnail(video_path="sample.mp4")

    assert failed["status"] == "failed"
    assert failed["error"] == "ffmpeg boom"


@pytest.mark.asyncio
async def test_generate_video_thumbnail_returns_failed_when_local_file_missing(monkeypatch):
    thumbnail_service = _thumbnail_service_module()
    service = thumbnail_service.ThumbnailService()
    temp_dir = _make_temp_dir()
    output_dir = temp_dir / "video-thumbs"
    frame_path = temp_dir / "frame.png"
    _create_image(frame_path, mode="RGB", size=(400, 300))

    monkeypatch.setattr(service, "_extract_video_frame", _async_return(str(frame_path)))
    original_exists = Path.exists

    def _fake_exists(path_obj):
        if str(path_obj).endswith("sample_thumb_small.webp"):
            return False
        return original_exists(path_obj)

    monkeypatch.setattr(Path, "exists", _fake_exists)

    result = await service.generate_video_thumbnail(
        video_path="sample.mp4",
        output_dir=str(output_dir),
        thumbnail_name="sample_thumb.webp",
    )

    assert result["status"] == "failed"
    assert "Thumbnail file not created" in result["error"]
    assert frame_path.exists() is False


@pytest.mark.asyncio
async def test_generate_video_thumbnail_defaults_to_storage_base_path(monkeypatch):
    thumbnail_service = _thumbnail_service_module()
    service = thumbnail_service.ThumbnailService()
    temp_dir = _make_temp_dir()
    storage_root = temp_dir / "storage-root"
    frame_path = temp_dir / "frame.png"
    _create_image(frame_path, mode="RGB", size=(400, 300))

    monkeypatch.setattr(service, "_extract_video_frame", _async_return(str(frame_path)))
    monkeypatch.setattr(
        thumbnail_service,
        "settings",
        SimpleNamespace(STORAGE_BASE_PATH=str(storage_root)),
    )

    result = await service.generate_video_thumbnail(video_path="demo.mp4")

    assert result["status"] == "ready"
    assert (storage_root / "thumbnails" / "demo_thumb_small.webp").exists()
    assert (storage_root / "thumbnails" / "demo_thumb_medium.webp").exists()
    assert (storage_root / "thumbnails" / "demo_thumb_large.webp").exists()


@pytest.mark.asyncio
async def test_validate_thumbnail_checks_existence_type_and_size():
    thumbnail_service = _thumbnail_service_module()
    service = thumbnail_service.ThumbnailService()
    temp_dir = _make_temp_dir()
    valid_path = temp_dir / "valid.bmp"
    invalid_path = temp_dir / "invalid.txt"
    small_path = temp_dir / "small.bmp"

    _create_image(valid_path, mode="RGB", size=(200, 200), image_format="BMP")
    _create_image(small_path, mode="RGB", size=(5, 5), image_format="BMP")
    invalid_path.write_text("not an image", encoding="utf-8")

    assert await service.validate_thumbnail(str(valid_path)) is True
    assert await service.validate_thumbnail(str(temp_dir / "missing.webp")) is False
    assert await service.validate_thumbnail(str(invalid_path)) is False
    assert await service.validate_thumbnail(str(small_path)) is False


def _thumbnail_service_module():
    return importlib.import_module("app.services.thumbnail_service")


def _make_temp_dir() -> Path:
    root = Path("e:/Project/ARV/.pytest-temp") / f"thumbnail-service-{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _create_image(path: Path, mode: str, size: tuple[int, int], image_format: str | None = None):
    image = Image.new(mode, size, (255, 0, 0, 128) if "A" in mode else (255, 0, 0))
    image.save(path, format=image_format)


def _async_return(value):
    async def _inner(*args, **kwargs):
        return value

    return _inner


def _async_raise(exc):
    async def _inner(*args, **kwargs):
        raise exc

    return _inner
