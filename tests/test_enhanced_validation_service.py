import importlib
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import numpy as np
import pytest
from PIL import Image


def test_validation_result_defaults_and_constraints_lookup():
    service_module = _service_module()
    result = service_module.ValidationResult()
    service = service_module.EnhancedValidationService()

    assert result.is_valid is True
    assert result.validation_level == service_module.ValidationLevel.BASIC
    assert service._get_constraints("image") == service.image_constraints
    assert service._get_constraints("video") == service.video_constraints
    assert service._get_constraints("unknown") is None


@pytest.mark.asyncio
async def test_detect_file_type_prefers_magic_and_falls_back(monkeypatch):
    service_module = _service_module()
    service = service_module.EnhancedValidationService()
    temp_dir = _make_temp_dir()
    image_path = temp_dir / "sample.bin"
    image_path.write_bytes(b"fake")

    monkeypatch.setattr(service_module.magic, "from_file", lambda *args, **kwargs: "image/png")
    assert await service._detect_file_type(image_path) == "image"

    monkeypatch.setattr(service_module.magic, "from_file", _raise_sync(RuntimeError("no magic")))
    monkeypatch.setattr(service_module, "imghdr", SimpleNamespace(what=lambda *args, **kwargs: "png"))
    assert await service._detect_file_type(image_path) == "image"

    monkeypatch.setattr(service_module, "imghdr", SimpleNamespace(what=_raise_sync(RuntimeError("no imghdr"))))

    class _FakeCapture:
        def isOpened(self):
            return True

        def release(self):
            return None

    monkeypatch.setattr(service_module.cv2, "VideoCapture", lambda *args, **kwargs: _FakeCapture())
    assert await service._detect_file_type(image_path) == "video"

    class _ClosedCapture:
        def isOpened(self):
            return False

    monkeypatch.setattr(service_module.cv2, "VideoCapture", lambda *args, **kwargs: _ClosedCapture())
    assert await service._detect_file_type(image_path, "photo.JPG") == "image"
    assert await service._detect_file_type(image_path, "clip.MP4") == "video"
    assert await service._detect_file_type(image_path, "archive.bin") == "unknown"


@pytest.mark.asyncio
async def test_basic_validation_handles_success_failures_and_mime_warning(monkeypatch):
    service_module = _service_module()
    service = service_module.EnhancedValidationService()
    temp_dir = _make_temp_dir()
    image_path = temp_dir / "photo.png"
    image_path.write_bytes(b"abc")
    result = service_module.ValidationResult()

    monkeypatch.setattr(service_module.magic, "from_file", lambda *args, **kwargs: "image/png")
    await service._basic_validation(image_path, service.image_constraints, result)

    assert result.is_valid is True
    assert result.file_info["extension"] == "png"
    assert result.file_info["mime_type"] == "image/png"

    empty_path = temp_dir / "empty.exe"
    empty_path.write_bytes(b"")
    failing = service_module.ValidationResult()
    monkeypatch.setattr(service_module.magic, "from_file", _raise_sync(RuntimeError("magic failed")))
    await service._basic_validation(empty_path, service.image_constraints, failing)

    assert failing.is_valid is False
    assert "File is empty" in failing.errors
    assert "Extension not allowed: exe" in failing.errors
    assert any("Could not detect MIME type" in warning for warning in failing.warnings)


@pytest.mark.asyncio
async def test_validate_image_content_extracts_metadata_and_suspicious_exif():
    service_module = _service_module()
    service = service_module.EnhancedValidationService()
    temp_dir = _make_temp_dir()
    image_path = temp_dir / "suspicious.jpg"

    exif = Image.Exif()
    exif[270] = "javascript:alert(1)"
    Image.new("RGB", (320, 240), (50, 60, 70)).save(image_path, format="JPEG", exif=exif)

    result = service_module.ValidationResult()
    await service._validate_image_content(image_path, service.image_constraints, result)

    assert result.is_valid is True
    assert result.metadata["format"] == "JPEG"
    assert result.file_info["width"] == 320
    assert result.security_info == {}
    assert result.threat_level == service_module.ThreatLevel.SUSPICIOUS
    assert any("Suspicious content in EXIF" in warning for warning in result.warnings)


@pytest.mark.asyncio
async def test_validate_image_content_handles_invalid_and_anomalies():
    service_module = _service_module()
    service = service_module.EnhancedValidationService()
    temp_dir = _make_temp_dir()
    tiny_path = temp_dir / "tiny.png"
    broken_path = temp_dir / "broken.png"
    Image.new("RGB", (20, 20), (0, 0, 0)).save(tiny_path, format="PNG")
    broken_path.write_text("not-an-image", encoding="utf-8")

    tiny_result = service_module.ValidationResult()
    await service._validate_image_content(tiny_path, service.image_constraints, tiny_result)
    broken_result = service_module.ValidationResult()
    await service._validate_image_content(broken_path, service.image_constraints, broken_result)

    assert tiny_result.is_valid is False
    assert any("Resolution too small" in error for error in tiny_result.errors)
    assert any("Image appears to be a solid color" in warning for warning in tiny_result.warnings)
    assert any("Very small image" in warning for warning in tiny_result.warnings)
    assert broken_result.is_valid is False
    assert any("Invalid image file" in error for error in broken_result.errors)


@pytest.mark.asyncio
async def test_validate_video_content_success_and_ffprobe_failures(monkeypatch):
    service_module = _service_module()
    service = service_module.EnhancedValidationService()
    temp_dir = _make_temp_dir()
    video_path = temp_dir / "clip.mp4"
    video_path.write_bytes(b"video")

    async def _fake_anomalies(file_path, result):
        result.warnings.append("checked anomalies")

    monkeypatch.setattr(service, "_detect_video_anomalies", _fake_anomalies)
    monkeypatch.setattr(
        service_module.asyncio,
        "create_subprocess_exec",
        _async_return(
            _FakeProcess(
                returncode=0,
                stdout=json.dumps(
                    {
                        "format": {"duration": "12.5", "bit_rate": "64000"},
                        "streams": [
                            {
                                "codec_type": "video",
                                "codec_name": "h264",
                                "width": 1280,
                                "height": 720,
                                "r_frame_rate": "30",
                                "pix_fmt": "yuv420p",
                                "nb_frames": "150",
                            }
                        ],
                    }
                ).encode("utf-8"),
            )
        ),
    )

    result = service_module.ValidationResult()
    await service._validate_video_content(video_path, service.video_constraints, result)

    assert result.is_valid is True
    assert result.metadata["codec"] == "h264"
    assert result.metadata["fps"] == 30
    assert result.file_info["duration"] == 12.5
    assert "checked anomalies" in result.warnings

    invalid_result = service_module.ValidationResult()
    monkeypatch.setattr(
        service_module.asyncio,
        "create_subprocess_exec",
        _async_return(_FakeProcess(returncode=1, stderr=b"broken file")),
    )
    await service._validate_video_content(video_path, service.video_constraints, invalid_result)
    assert invalid_result.is_valid is False
    assert any("Invalid video file" in error for error in invalid_result.errors)

    missing_stream_result = service_module.ValidationResult()
    monkeypatch.setattr(
        service_module.asyncio,
        "create_subprocess_exec",
        _async_return(_FakeProcess(returncode=0, stdout=b'{"format": {}, "streams": []}')),
    )
    await service._validate_video_content(video_path, service.video_constraints, missing_stream_result)
    assert missing_stream_result.is_valid is False
    assert "No video stream found" in missing_stream_result.errors


@pytest.mark.asyncio
async def test_detect_video_anomalies_and_error_path(monkeypatch):
    service_module = _service_module()
    service = service_module.EnhancedValidationService()
    result = service_module.ValidationResult()

    class _Capture:
        def __init__(self):
            self.position = 0

        def get(self, prop):
            return 2 if prop == service_module.cv2.CAP_PROP_FRAME_COUNT else 0

        def set(self, prop, value):
            self.position = value

        def read(self):
            frame = np.zeros((4, 4, 3), dtype=np.uint8)
            return True, frame

        def release(self):
            return None

    monkeypatch.setattr(service_module.cv2, "VideoCapture", lambda *args, **kwargs: _Capture())
    await service._detect_video_anomalies(Path("clip.mp4"), result)

    assert "Video starts with black frame" in result.warnings
    assert "Video ends with black frame" in result.warnings

    no_frames = service_module.ValidationResult()

    class _NoFramesCapture:
        def get(self, prop):
            return 0

        def release(self):
            return None

    monkeypatch.setattr(service_module.cv2, "VideoCapture", lambda *args, **kwargs: _NoFramesCapture())
    await service._detect_video_anomalies(Path("clip.mp4"), no_frames)
    assert no_frames.is_valid is False
    assert "Video has no frames" in no_frames.errors

    warning_result = service_module.ValidationResult()
    monkeypatch.setattr(service_module.cv2, "VideoCapture", _raise_sync(RuntimeError("cv failure")))
    await service._detect_video_anomalies(Path("clip.mp4"), warning_result)
    assert any("Could not analyze video anomalies" in warning for warning in warning_result.warnings)


@pytest.mark.asyncio
async def test_comprehensive_and_paranoid_validation_dispatch(monkeypatch):
    service_module = _service_module()
    service = service_module.EnhancedValidationService()
    calls = []

    async def _record(name):
        async def _inner(*args, **kwargs):
            calls.append(name)
        return _inner

    monkeypatch.setattr(service, "_virus_scan", await _record("virus"))
    monkeypatch.setattr(service, "_deep_image_analysis", await _record("deep_image"))
    monkeypatch.setattr(service, "_deep_video_analysis", await _record("deep_video"))
    monkeypatch.setattr(service, "_check_metadata_sanitization", await _record("metadata"))
    monkeypatch.setattr(service, "_analyze_file_signatures", await _record("signatures"))
    monkeypatch.setattr(service, "_entropy_analysis", await _record("entropy"))
    monkeypatch.setattr(service, "_behavioral_analysis", await _record("behavior"))

    await service._comprehensive_validation(Path("photo.png"), "image", service_module.ValidationResult())
    await service._comprehensive_validation(Path("clip.mp4"), "video", service_module.ValidationResult())
    await service._paranoid_validation(Path("photo.png"), "image", service_module.ValidationResult())
    await service._paranoid_validation(Path("clip.mp4"), "video", service_module.ValidationResult())

    assert calls == [
        "virus",
        "deep_image",
        "metadata",
        "virus",
        "deep_video",
        "metadata",
        "signatures",
        "entropy",
        "behavior",
        "signatures",
        "behavior",
    ]


@pytest.mark.asyncio
async def test_virus_scan_signature_entropy_and_behavior_paths(monkeypatch):
    service_module = _service_module()
    service = service_module.EnhancedValidationService()
    temp_dir = _make_temp_dir()
    jpeg_path = temp_dir / "photo.jpg"
    jpeg_path.write_bytes(b"\xFF\xD8\xFF" + bytes(range(100)))

    clean_result = service_module.ValidationResult()
    monkeypatch.setattr(
        service_module.asyncio,
        "create_subprocess_exec",
        _async_return(_FakeProcess(returncode=0, stdout=b"clean")),
    )
    await service._virus_scan(jpeg_path, clean_result)
    assert clean_result.security_info["virus_scan"] == "clean"

    infected_result = service_module.ValidationResult()
    monkeypatch.setattr(
        service_module.asyncio,
        "create_subprocess_exec",
        _async_return(_FakeProcess(returncode=1, stdout=b"infected")),
    )
    await service._virus_scan(jpeg_path, infected_result)
    assert infected_result.is_valid is False
    assert infected_result.threat_level == service_module.ThreatLevel.MALICIOUS

    failed_result = service_module.ValidationResult()
    monkeypatch.setattr(
        service_module.asyncio,
        "create_subprocess_exec",
        _async_return(_FakeProcess(returncode=2, stderr=b"engine down")),
    )
    await service._virus_scan(jpeg_path, failed_result)
    assert failed_result.security_info["virus_scan"] == "failed"

    unavailable_result = service_module.ValidationResult()
    monkeypatch.setattr(service_module.asyncio, "create_subprocess_exec", _async_raise(RuntimeError("missing clamd")))
    await service._virus_scan(jpeg_path, unavailable_result)
    assert unavailable_result.security_info["virus_scan"] == "unavailable"

    signature_result = service_module.ValidationResult()
    await service._analyze_file_signatures(jpeg_path, signature_result)
    assert signature_result.security_info["file_signature"] == "JPEG"

    unknown_path = temp_dir / "unknown.bin"
    unknown_path.write_bytes(b"not-a-known-header")
    unknown_sig = service_module.ValidationResult()
    await service._analyze_file_signatures(unknown_path, unknown_sig)
    assert unknown_sig.security_info["file_signature"] == "unknown"
    assert "Unknown file signature" in unknown_sig.warnings

    entropy_result = service_module.ValidationResult()
    noisy_path = temp_dir / "entropy.bin"
    noisy_path.write_bytes(bytes(range(256)) * 4)
    await service._entropy_analysis(noisy_path, entropy_result)
    assert entropy_result.metadata["entropy"] > 7.8
    assert entropy_result.threat_level == service_module.ThreatLevel.SUSPICIOUS

    behavioral = service_module.ValidationResult()
    await service._behavioral_analysis(jpeg_path, behavioral)
    assert behavioral.security_info["behavioral_analysis"] == "completed"


@pytest.mark.asyncio
async def test_deep_image_and_video_analysis_paths(monkeypatch):
    service_module = _service_module()
    service = service_module.EnhancedValidationService()
    result = service_module.ValidationResult()
    image = np.zeros((12, 12, 3), dtype=np.uint8)

    monkeypatch.setattr(service_module.cv2, "imread", lambda *args, **kwargs: image)
    monkeypatch.setattr(service_module.cv2, "calcHist", lambda *args, **kwargs: np.ones((8, 8, 8), dtype=np.float32))
    monkeypatch.setattr(service_module.cv2, "normalize", lambda hist, *_args, **_kwargs: hist)
    monkeypatch.setattr(service_module.cv2, "cvtColor", lambda img, code: np.zeros((12, 12), dtype=np.uint8))
    monkeypatch.setattr(service_module.cv2, "Canny", lambda *args, **kwargs: np.zeros((12, 12), dtype=np.uint8))
    monkeypatch.setattr(service_module.cv2, "Laplacian", lambda *args, **kwargs: np.ones((12, 12), dtype=np.float64))

    await service._deep_image_analysis(Path("photo.png"), result)

    assert "color_histogram" in result.metadata
    assert result.metadata["edge_density"] == 0.0
    assert any("Very low edge density" in warning for warning in result.warnings)

    bright_result = service_module.ValidationResult()

    class _VideoCapture:
        def __init__(self):
            self.total_frames = 4

        def get(self, prop):
            return self.total_frames

        def set(self, prop, value):
            return None

        def read(self):
            return True, np.full((3, 3, 3), 255, dtype=np.uint8)

        def release(self):
            return None

    monkeypatch.setattr(service_module.cv2, "VideoCapture", lambda *args, **kwargs: _VideoCapture())
    await service._deep_video_analysis(Path("clip.mp4"), bright_result)

    assert bright_result.metadata["avg_brightness"] == 255.0
    assert any("very bright" in warning.lower() for warning in bright_result.warnings)

    error_result = service_module.ValidationResult()
    monkeypatch.setattr(service_module.cv2, "imread", _raise_sync(RuntimeError("cv read failed")))
    await service._deep_image_analysis(Path("photo.png"), error_result)
    assert any("Deep image analysis failed" in warning for warning in error_result.warnings)


@pytest.mark.asyncio
async def test_validate_file_orchestration_and_error_paths(monkeypatch):
    service_module = _service_module()
    service = service_module.EnhancedValidationService()
    temp_dir = _make_temp_dir()
    existing = temp_dir / "photo.png"
    existing.write_bytes(b"ok")
    missing = temp_dir / "missing.png"

    missing_result = await service.validate_file(str(missing))
    assert missing_result.is_valid is False
    assert missing_result.errors == ["File does not exist"]

    monkeypatch.setattr(service, "_detect_file_type", _async_return("unsupported"))
    unsupported = await service.validate_file(str(existing), file_type="auto")
    assert unsupported.is_valid is False
    assert unsupported.errors == ["Unsupported file type: unsupported"]

    order = []

    async def _basic(file_path, constraints, result):
        order.append("basic")

    async def _standard(file_path, file_type, constraints, result):
        order.append("standard")

    async def _comprehensive(file_path, file_type, result):
        order.append("comprehensive")
        result.warnings.append("careful")

    async def _paranoid(file_path, file_type, result):
        order.append("paranoid")

    monkeypatch.setattr(service, "_basic_validation", _basic)
    monkeypatch.setattr(service, "_standard_validation", _standard)
    monkeypatch.setattr(service, "_comprehensive_validation", _comprehensive)
    monkeypatch.setattr(service, "_paranoid_validation", _paranoid)
    monkeypatch.setattr(service, "_assess_threat_level", lambda result: service_module.ThreatLevel.SUSPICIOUS)

    basic = await service.validate_file(str(existing), file_type="image", validation_level=service_module.ValidationLevel.BASIC)
    standard = await service.validate_file(str(existing), file_type="image", validation_level=service_module.ValidationLevel.STANDARD)
    comprehensive = await service.validate_file(str(existing), file_type="image", validation_level=service_module.ValidationLevel.COMPREHENSIVE)
    paranoid = await service.validate_file(str(existing), file_type="image", validation_level=service_module.ValidationLevel.PARANOID)

    assert basic.validation_level == service_module.ValidationLevel.BASIC
    assert standard.validation_level == service_module.ValidationLevel.STANDARD
    assert comprehensive.validation_level == service_module.ValidationLevel.COMPREHENSIVE
    assert paranoid.threat_level == service_module.ThreatLevel.SUSPICIOUS
    assert order == [
        "basic",
        "basic", "standard",
        "basic", "standard", "comprehensive",
        "basic", "standard", "comprehensive", "paranoid",
    ]

    monkeypatch.setattr(service, "_basic_validation", _async_raise(RuntimeError("boom")))
    failed = await service.validate_file(str(existing), file_type="image")
    assert failed.is_valid is False
    assert any("Validation failed: boom" in error for error in failed.errors)


@pytest.mark.asyncio
async def test_batch_validate_and_summary(monkeypatch):
    service_module = _service_module()
    service = service_module.EnhancedValidationService()

    async def _fake_validate(path, validation_level=None):
        if path == "bad":
            raise RuntimeError("kaput")
        return service_module.ValidationResult(
            is_valid=path != "invalid",
            threat_level=service_module.ThreatLevel.SAFE if path == "good" else service_module.ThreatLevel.MALICIOUS,
            warnings=["warn"] if path == "invalid" else [],
            errors=["err"] if path == "invalid" else [],
            validation_time=2.0 if path == "good" else 4.0,
            validation_level=validation_level,
        )

    monkeypatch.setattr(service, "validate_file", _fake_validate)
    results = await service.batch_validate(
        ["good", "invalid", "bad"],
        validation_level=service_module.ValidationLevel.PARANOID,
    )
    summary = service.get_validation_summary(results)

    assert len(results) == 3
    assert results[2].is_valid is False
    assert "Validation exception: kaput" in results[2].errors[0]
    assert summary["total_files"] == 3
    assert summary["valid_files"] == 1
    assert summary["invalid_files"] == 2
    assert round(summary["success_rate"], 2) == 33.33
    assert summary["threat_distribution"]["safe"] == 1
    assert summary["threat_distribution"]["malicious"] == 1
    assert summary["threat_distribution"]["unknown"] == 1
    assert summary["total_warnings"] == 1
    assert summary["total_errors"] == 2


def _service_module():
    return importlib.import_module("app.services.enhanced_validation_service")


def _make_temp_dir() -> Path:
    root = Path("e:/Project/ARV/.pytest-temp") / f"enhanced-validation-{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root


class _FakeProcess:
    def __init__(self, returncode=0, stdout=b"", stderr=b""):
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr

    async def communicate(self):
        return self._stdout, self._stderr


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
