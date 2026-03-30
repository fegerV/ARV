from pathlib import Path
from types import SimpleNamespace
import shutil
import uuid

import pytest
from PIL import Image

from app.utils import ar_content as mod


def test_sanitize_filename_and_storage_builders(monkeypatch):
    monkeypatch.setattr(mod.settings, "STORAGE_BASE_PATH", "storage-root")
    monkeypatch.setattr(mod, "generate_slug", lambda value: "transliterated-slug")

    assert mod.sanitize_filename("") == "unnamed"
    assert mod.sanitize_filename(' bad<>:"/\\|?*\x00..name ') == "bad_name"
    assert mod.sanitize_filename("a" * 120, max_length=10) == "a" * 10

    path = mod.build_ar_content_storage_path(
        company_id=1,
        project_id=2,
        order_number="ORD/001",
        project_name="Проект",
    )
    assert path == Path("storage-root") / "VertexAR" / "transliterated-slug" / "ORD001"

    monkeypatch.setattr(mod, "generate_slug", lambda value: "")
    fallback = mod.build_ar_content_storage_path(
        company_id=1,
        project_id=2,
        order_number="001",
        project_name="name with spaces",
    )
    assert fallback == Path("storage-root") / "VertexAR" / "name_with_spaces" / "001"

    default_project = mod.build_ar_content_storage_path(1, 7, "42")
    assert default_project == Path("storage-root") / "VertexAR" / "Project_7" / "42"


@pytest.mark.asyncio
async def test_get_ar_content_storage_path_with_loaded_relations_and_db(monkeypatch):
    monkeypatch.setattr(mod.settings, "STORAGE_BASE_PATH", "storage-root")
    monkeypatch.setattr(mod, "generate_slug", lambda value: value.lower())

    ar = SimpleNamespace(
        id=10,
        company_id=1,
        project_id=2,
        order_number="A-01",
        company=SimpleNamespace(name="LoadedCompany"),
        project=SimpleNamespace(name="LoadedProject"),
    )
    loaded = await mod.get_ar_content_storage_path(ar)
    assert loaded == Path("storage-root") / "VertexAR" / "loadedproject" / "A-01"

    missing_relations = SimpleNamespace(
        id=11,
        company_id=1,
        project_id=2,
        order_number="B-02",
        company=None,
        project=None,
    )
    db = SimpleNamespace(
        execute=_async_return(
            SimpleNamespace(
                scalar_one=lambda: SimpleNamespace(
                    company=SimpleNamespace(name="DbCompany"),
                    project=SimpleNamespace(name="DbProject"),
                )
            )
        )
    )

    from app.models.ar_content import ARContent

    resolved = await mod.get_ar_content_storage_path(missing_relations, db=db)
    assert resolved == Path("storage-root") / "VertexAR" / "dbproject" / "B-02"
    assert ARContent is not None


def test_public_url_and_validators(monkeypatch):
    monkeypatch.setattr(mod.settings, "STORAGE_BASE_PATH", "base-storage")
    provider = SimpleNamespace(get_public_url=lambda rel: f"/public/{rel}")

    under_base = mod.build_public_url(Path("base-storage") / "VertexAR" / "p" / "file.png", provider=provider)
    assert under_base == "/public/VertexAR/p/file.png"

    vertex_path = mod.build_public_url(Path("/opt/data/VertexAR/demo/file.png"), provider=provider)
    assert vertex_path == "/public/VertexAR/demo/file.png"

    fallback = mod.build_public_url(Path("/opt/data/file.png"), provider=provider)
    assert fallback == "/storage/file.png"

    assert mod.build_unique_link("abc-123") == "/view/abc-123"
    assert mod.validate_email_format("user@example.com") is True
    assert mod.validate_email_format("bad-email") is False
    assert mod.validate_file_extension("photo.PNG", ["png", "jpg"]) is True
    assert mod.validate_file_extension("photo.exe", ["png", "jpg"]) is False
    assert mod.validate_file_size(100, 100) is True
    assert mod.validate_file_size(101, 100) is False


@pytest.mark.asyncio
async def test_generate_qr_code_and_save_uploaded_file_local(monkeypatch):
    workdir = _make_workspace_tempdir()
    try:
        monkeypatch.setattr(mod.settings, "PUBLIC_URL", "https://example.com/")
        monkeypatch.setattr(mod.settings, "STORAGE_BASE_PATH", str(workdir))
        provider = SimpleNamespace(get_public_url=lambda rel: f"/public/{rel}")

        qr_dir = workdir / "VertexAR" / "demo" / "001"
        qr_url = await mod.generate_qr_code("unique-id", qr_dir, provider=provider)
        assert qr_url == "/public/VertexAR/demo/001/qr_code.png"
        assert (qr_dir / "qr_code.png").exists()

        upload = _UploadFile([b"hello ", b"world"])
        destination = workdir / "VertexAR" / "demo" / "001" / "marker.bin"
        result = await mod.save_uploaded_file(upload, destination, provider=None)
        assert result is None
        assert destination.read_bytes() == b"hello world"
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


@pytest.mark.asyncio
async def test_generate_qr_code_save_uploaded_file_and_thumbnail_remote(monkeypatch):
    saved = {}

    class FakeYandexProvider:
        async def save_file_bytes(self, content, dest):
            saved[dest] = content
            return f"yadisk://{dest}"

    monkeypatch.setitem(
        __import__("sys").modules,
        "app.core.yandex_disk_provider",
        SimpleNamespace(YandexDiskStorageProvider=FakeYandexProvider),
    )
    monkeypatch.setattr(mod.settings, "PUBLIC_URL", "https://example.com")

    provider = FakeYandexProvider()
    qr_result = await mod.generate_qr_code("uid-1", Path("VertexAR/demo/002"), provider=provider)
    assert qr_result == "yadisk://VertexAR/demo/002/qr_code.png"
    assert "VertexAR/demo/002/qr_code.png" in saved

    upload = _UploadFile([b"remote-bytes"])
    remote_result = await mod.save_uploaded_file(
        upload,
        Path("unused.bin"),
        provider=provider,
        relative_storage_path="VertexAR/demo/002/file.bin",
    )
    assert remote_result == "yadisk://VertexAR/demo/002/file.bin"

    workdir = _make_workspace_tempdir()
    try:
        image_path = workdir / "source.png"
        _write_sample_image(image_path)

        thumb_remote = await mod.generate_thumbnail(
            image_path=image_path,
            thumbnail_path=workdir / "thumb.png",
            provider=provider,
            relative_storage_path="VertexAR/demo/002/thumb.png",
        )
        assert thumb_remote == "yadisk://VertexAR/demo/002/thumb.png"
        assert "VertexAR/demo/002/thumb.png" in saved
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


@pytest.mark.asyncio
async def test_generate_thumbnail_local():
    workdir = _make_workspace_tempdir()
    try:
        image_path = workdir / "source.png"
        thumb_path = workdir / "thumb.png"
        _write_sample_image(image_path, size=(400, 240))

        result = await mod.generate_thumbnail(image_path, thumb_path, size=(120, 120))
        assert result is None
        assert thumb_path.exists()

        with Image.open(thumb_path) as thumb:
            assert thumb.size == (120, 120)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


class _UploadFile:
    def __init__(self, chunks):
        self._chunks = list(chunks)

    async def read(self, _size=-1):
        if self._chunks:
            return self._chunks.pop(0)
        return b""


def _write_sample_image(path: Path, size=(320, 320)) -> None:
    image = Image.new("RGB", size, "white")
    image.putpixel((0, 0), (255, 0, 0))
    image.putpixel((size[0] - 1, size[1] - 1), (0, 0, 255))
    image.save(path, format="PNG")


def _make_workspace_tempdir() -> Path:
    base = Path("codex_tmp_test")
    base.mkdir(exist_ok=True)
    path = base / f"ar_content_{uuid.uuid4().hex}"
    path.mkdir()
    return path


def _async_return(value):
    async def _inner(*args, **kwargs):
        return value

    return _inner
