import asyncio
import json
from pathlib import Path
import shutil
import uuid

import pytest
from fastapi import HTTPException

from app.utils import video_utils as mod


def test_validate_video_file_allows_supported_and_rejects_invalid():
    mod.validate_video_file(_UploadFile("clip.mp4", "video/mp4", []))

    with pytest.raises(HTTPException) as mime_error:
        mod.validate_video_file(_UploadFile("clip.mp4", "application/octet-stream", []))
    assert mime_error.value.status_code == 400
    assert "Unsupported MIME type" in mime_error.value.detail

    with pytest.raises(HTTPException) as ext_error:
        mod.validate_video_file(_UploadFile("clip.exe", "video/mp4", []))
    assert ext_error.value.status_code == 400
    assert "Unsupported file extension" in ext_error.value.detail


@pytest.mark.asyncio
async def test_get_video_metadata_success_and_middle_frame(monkeypatch):
    workdir = _make_workspace_tempdir()
    try:
        video_path = workdir / "video.mp4"
        video_path.write_bytes(b"0" * 128)

        probe_payload = {
            "format": {"duration": "12.5", "format_name": "mov,mp4", "bit_rate": "2048"},
            "streams": [{"codec_type": "video", "width": 1920, "height": 1080, "codec_name": "h264", "r_frame_rate": "30000/1001"}],
        }
        monkeypatch.setattr(
            mod.asyncio,
            "create_subprocess_exec",
            _async_return(_Process(0, json.dumps(probe_payload).encode(), b"")),
        )

        metadata = await mod.get_video_metadata(str(video_path))
        assert metadata == {
            "duration": 12.5,
            "width": 1920,
            "height": 1080,
            "size_bytes": 128,
            "mime_type": "mov,mp4",
            "codec": "h264",
            "fps": pytest.approx(29.97002997),
            "bit_rate": 2048,
        }
        assert await mod.get_video_middle_frame_time(str(video_path)) == 6.25
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


@pytest.mark.asyncio
async def test_get_video_metadata_error_paths_and_middle_frame_fallback(monkeypatch):
    workdir = _make_workspace_tempdir()
    try:
        video_path = workdir / "video.mp4"
        video_path.write_bytes(b"0" * 64)

        monkeypatch.setattr(
            mod.asyncio,
            "create_subprocess_exec",
            _raise_file_not_found,
        )
        missing_ffprobe = await mod.get_video_metadata(str(video_path))
        assert missing_ffprobe["size_bytes"] == 64
        assert missing_ffprobe["codec"] == "unknown"

        monkeypatch.setattr(
            mod.asyncio,
            "create_subprocess_exec",
            _async_return(_Process(1, b"", b"ffprobe bad")),
        )
        with pytest.raises(RuntimeError, match="ffprobe failed"):
            await mod.get_video_metadata(str(video_path))

        monkeypatch.setattr(
            mod.asyncio,
            "create_subprocess_exec",
            _async_return(_Process(0, b"{bad-json", b"")),
        )
        with pytest.raises(RuntimeError, match="Failed to parse ffprobe output"):
            await mod.get_video_metadata(str(video_path))

        monkeypatch.setattr(
            mod.asyncio,
            "create_subprocess_exec",
            _async_return(_Process(0, json.dumps({"format": {}}).encode(), b"")),
        )
        with pytest.raises(RuntimeError, match="No video stream found"):
            await mod.get_video_metadata(str(video_path))

        monkeypatch.setattr(mod, "get_video_metadata", _async_return({"duration": 0}))
        assert await mod.get_video_middle_frame_time(str(video_path)) == 1.0
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


@pytest.mark.asyncio
async def test_save_uploaded_video_success_size_limit_and_io_error():
    workdir = _make_workspace_tempdir()
    try:
        destination = workdir / "videos" / "clip.mp4"
        upload = _UploadFile("clip.mp4", "video/mp4", [b"a" * 5, b"b" * 7])
        await mod.save_uploaded_video(upload, destination)
        assert destination.read_bytes() == b"a" * 5 + b"b" * 7

        too_large = _UploadFile("big.mp4", "video/mp4", [b"a" * (mod.MAX_VIDEO_SIZE + 1)])
        with pytest.raises(HTTPException) as too_large_error:
            await mod.save_uploaded_video(too_large, workdir / "videos" / "big.mp4")
        assert too_large_error.value.status_code == 413

        blocked_dir = workdir / "blocked"
        blocked_dir.mkdir()
        with pytest.raises(HTTPException) as io_error:
            await mod.save_uploaded_video(_UploadFile("x.mp4", "video/mp4", [b"123"]), blocked_dir)
        assert io_error.value.status_code == 500
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def test_generate_video_filename_variants():
    assert mod.generate_video_filename("My Clip.mp4") == "my_clip.mp4"
    assert mod.generate_video_filename("My-Clip.mov", video_id=42) == "video_42.mov"

    with pytest.raises(ValueError, match="Unsupported file extension"):
        mod.generate_video_filename("bad.txt")


class _UploadFile:
    def __init__(self, filename, content_type, chunks):
        self.filename = filename
        self.content_type = content_type
        self._chunks = list(chunks)

    async def read(self, _size=-1):
        if self._chunks:
            return self._chunks.pop(0)
        return b""


class _Process:
    def __init__(self, returncode, stdout, stderr):
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr

    async def communicate(self):
        return self._stdout, self._stderr


async def _raise_file_not_found(*args, **kwargs):
    raise FileNotFoundError("ffprobe missing")


def _async_return(value):
    async def _inner(*args, **kwargs):
        return value

    return _inner


def _make_workspace_tempdir() -> Path:
    base = Path("codex_tmp_test")
    base.mkdir(exist_ok=True)
    path = base / f"video_utils_{uuid.uuid4().hex}"
    path.mkdir()
    return path
