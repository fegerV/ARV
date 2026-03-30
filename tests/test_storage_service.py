from pathlib import Path
import builtins
import shutil
import uuid

import pytest

from app.services import storage as mod


def test_local_storage_adapter_save_get_delete_and_public_url(monkeypatch):
    workdir = _make_workspace_tempdir()
    try:
        adapter = mod.LocalStorageAdapter(
            base_path=str(workdir),
            public_url_base="https://cdn.example.com/storage/",
        )

        public_url = adapter.save_file("folder/demo.txt", b"hello world", content_type="text/plain")
        assert public_url == "https://cdn.example.com/storage/folder/demo.txt"
        assert (workdir / "folder" / "demo.txt").read_bytes() == b"hello world"

        assert adapter.get_file("folder/demo.txt") == b"hello world"
        assert adapter.get_public_url("/folder/demo.txt") == "https://cdn.example.com/storage/folder/demo.txt"

        assert adapter.delete_file("folder/demo.txt") is True
        assert not (workdir / "folder" / "demo.txt").exists()
        assert adapter.delete_file("folder/demo.txt") is False
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def test_local_storage_adapter_directory_delete_and_missing_file():
    workdir = _make_workspace_tempdir()
    try:
        adapter = mod.LocalStorageAdapter(base_path=str(workdir), public_url_base="/storage")
        nested = workdir / "folder" / "nested"
        nested.mkdir(parents=True)
        (nested / "a.txt").write_bytes(b"a")

        assert adapter.delete_file("folder") is True
        assert not (workdir / "folder").exists()

        with pytest.raises(FileNotFoundError):
            adapter.get_file("folder/missing.txt")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def test_local_storage_adapter_storage_usage_and_fallback(monkeypatch):
    workdir = _make_workspace_tempdir()
    try:
        adapter = mod.LocalStorageAdapter(base_path=str(workdir), public_url_base="/storage")
        (workdir / "one.bin").write_bytes(b"a" * 10)
        (workdir / "two.bin").write_bytes(b"b" * 20)

        stats = adapter.get_storage_usage()
        assert stats["total_files"] == 2
        assert stats["total_size_bytes"] == 30
        assert stats["exists"] is True

        original_rglob = Path.rglob

        def _broken_rglob(self, pattern):
            if self == adapter.base_path:
                raise OSError("scan failed")
            return original_rglob(self, pattern)

        monkeypatch.setattr(Path, "rglob", _broken_rglob)
        failed = adapter.get_storage_usage()
        assert failed["total_files"] == 0
        assert failed["total_size_bytes"] == 0
        assert failed["exists"] is False
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def test_local_storage_adapter_save_get_and_delete_failure_paths(monkeypatch):
    workdir = _make_workspace_tempdir()
    try:
        adapter = mod.LocalStorageAdapter(base_path=str(workdir), public_url_base="/storage")
        adapter.save_file("demo.txt", b"ok")

        original_open = builtins.open

        def _broken_open(path, mode="r", *args, **kwargs):
            if str(path).endswith("broken-save.txt") and "wb" in mode:
                raise OSError("write failed")
            if str(path).endswith("demo.txt") and "rb" in mode:
                raise OSError("read failed")
            return original_open(path, mode, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", _broken_open)

        with pytest.raises(OSError):
            adapter.save_file("broken-save.txt", b"bad")

        with pytest.raises(OSError):
            adapter.get_file("demo.txt")

        monkeypatch.setattr(Path, "unlink", lambda self: (_ for _ in ()).throw(OSError("delete failed")))
        assert adapter.delete_file("demo.txt") is False
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def test_get_storage_adapter_singleton_and_reset(monkeypatch):
    mod.reset_storage_adapter()
    workdir = _make_workspace_tempdir()
    try:
        monkeypatch.setattr(mod.settings, "LOCAL_STORAGE_PATH", str(workdir))
        monkeypatch.setattr(mod.settings, "LOCAL_STORAGE_PUBLIC_URL", "/public")

        first = mod.get_storage_adapter()
        second = mod.get_storage_adapter()
        assert first is second
        assert first.base_path == workdir

        mod.reset_storage_adapter()
        third = mod.get_storage_adapter()
        assert third is not first
        assert third.base_path == workdir
    finally:
        mod.reset_storage_adapter()
        shutil.rmtree(workdir, ignore_errors=True)


def _make_workspace_tempdir() -> Path:
    base = Path("codex_tmp_test")
    base.mkdir(exist_ok=True)
    path = base / f"storage_{uuid.uuid4().hex}"
    path.mkdir()
    return path
