from pathlib import Path
from types import SimpleNamespace
import shutil
import sys
import uuid

import cv2
import numpy as np
import pytest

from app.services.marker_service import ARCoreMarkerService


@pytest.mark.asyncio
async def test_generate_marker_success_and_missing_file(monkeypatch):
    service = ARCoreMarkerService()
    workdir = _make_workspace_tempdir()
    try:
        image_path = workdir / "marker.png"
        _write_pattern_image(image_path)

        monkeypatch.setitem(
            sys.modules,
            "app.utils.ar_content",
            SimpleNamespace(build_public_url=lambda path: f"/media/{Path(path).name}"),
        )

        result = await service.generate_marker(1, str(image_path), workdir)
        assert result["status"] == "ready"
        assert result["marker_path"] == str(image_path)
        assert result["marker_url"] == "/media/marker.png"

        missing = await service.generate_marker(1, str(workdir / "missing.png"), workdir)
        assert missing == {"status": "failed", "error": "Photo file not found"}
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def test_quality_helpers_and_probability_ranges():
    service = ARCoreMarkerService()

    assert service.get_quality_level(None) == "unknown"
    assert service.get_quality_level(0.61) == "good"
    assert service.get_quality_level(0.35) == "fair"
    assert service.get_quality_level(0.2) == "poor"

    weak = {
        "brightness": 10,
        "contrast": 10,
        "sharpness": 5,
        "edge_density": 0.001,
        "recognition_probability": 0.1,
    }
    good = {
        "brightness": 128,
        "contrast": 80,
        "sharpness": 900,
        "edge_density": 0.2,
        "recognition_probability": 0.9,
    }

    assert service.should_auto_enhance(weak) is True
    assert service.should_auto_enhance(good) is False
    assert service.should_auto_enhance({}) is False

    recommendations = service.build_image_recommendations(weak)
    assert len(recommendations) >= 4
    assert service.build_image_recommendations(good) == [
        "Изображение выглядит подходящим для устойчивого трекинга"
    ]
    assert "проанализировать" in service.build_image_recommendations({})[0]

    assert service._estimate_recognition_probability(1000, 128, 2000, 1.0) == 1.0
    assert 0.0 <= service._estimate_recognition_probability(0, 0, 0, 0) <= 1.0


def test_analyze_image_quality_success_missing_and_exception(monkeypatch):
    service = ARCoreMarkerService()
    workdir = _make_workspace_tempdir()
    try:
        image_path = workdir / "quality.png"
        _write_pattern_image(image_path)

        result = service.analyze_image_quality(str(image_path))
        assert set(result) == {
            "brightness",
            "contrast",
            "sharpness",
            "edge_density",
            "recognition_probability",
        }
        assert 0.0 <= result["recognition_probability"] <= 1.0

        assert service.analyze_image_quality(str(workdir / "missing.png")) == {}

        monkeypatch.setattr("app.services.marker_service.cv2.imread", lambda *_args, **_kwargs: np.zeros((4, 4, 3), dtype=np.uint8))
        monkeypatch.setattr("app.services.marker_service.cv2.cvtColor", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("bad image")))
        assert service.analyze_image_quality(str(image_path)) == {}
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def test_enhance_image_for_marker_success_and_read_failure(monkeypatch):
    service = ARCoreMarkerService()
    workdir = _make_workspace_tempdir()
    try:
        source = workdir / "source.png"
        output = workdir / "nested" / "enhanced.png"
        _write_pattern_image(source)

        enhanced = service.enhance_image_for_marker(str(source), str(output))
        assert enhanced == str(output)
        assert output.exists()

        monkeypatch.setattr("app.services.marker_service.cv2.imread", lambda *_args, **_kwargs: None)
        assert service.enhance_image_for_marker(str(source), str(workdir / "failed.png")) is None
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


@pytest.mark.asyncio
async def test_validate_marker_size_window():
    service = ARCoreMarkerService()
    workdir = _make_workspace_tempdir()
    try:
        missing = await service.validate_marker(str(workdir / "missing.png"))
        assert missing is False

        too_small = workdir / "small.bin"
        too_small.write_bytes(b"0" * 100)
        assert await service.validate_marker(str(too_small)) is False

        valid = workdir / "valid.bin"
        valid.write_bytes(b"0" * 20000)
        assert await service.validate_marker(str(valid)) is True

        too_large = workdir / "large.bin"
        too_large.write_bytes(b"0" * 5_100_000)
        assert await service.validate_marker(str(too_large)) is False
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _write_pattern_image(path: Path) -> None:
    image = np.zeros((256, 256, 3), dtype=np.uint8)
    image[:, :128] = (255, 255, 255)
    cv2.rectangle(image, (32, 32), (224, 224), (0, 0, 255), 6)
    cv2.line(image, (0, 255), (255, 0), (0, 255, 0), 4)
    cv2.putText(image, "AR", (60, 140), cv2.FONT_HERSHEY_SIMPLEX, 2.2, (255, 0, 0), 5)
    cv2.imwrite(str(path), image)


def _make_workspace_tempdir() -> Path:
    base = Path("codex_tmp_test")
    base.mkdir(exist_ok=True)
    path = base / f"marker_{uuid.uuid4().hex}"
    path.mkdir()
    return path
