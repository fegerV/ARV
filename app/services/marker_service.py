from pathlib import Path
from typing import Optional
import structlog
import time
import cv2
import numpy as np

from app.core.config import settings
from app.core.storage import get_storage_provider_instance


logger = structlog.get_logger()


class ARCoreMarkerService:
    """
    Marker service for AR content (ARCore).
    Uses the photo image as the tracking target (raster JPEG/PNG). No .mind format.
    """

    _EDGE_DENSITY_TARGET = 0.2
    _CONTRAST_NORM = 50.0
    _SHARPNESS_NORM = 500.0
    _MIN_CONTRAST = 35.0
    _MIN_SHARPNESS = 60.0
    _MIN_RECOGNITION_PROBABILITY = 0.6

    async def generate_marker(
        self,
        ar_content_id: int,
        image_path: str,
        storage_path: Path,
        output_dir: str = None,  # Deprecated, kept for compatibility
    ) -> dict:
        """
        Return marker info from photo image (ARCore: marker = photo).
        No .mind file is generated.
        """
        from app.utils.ar_content import build_public_url
        path = Path(image_path)
        if not path.exists():
            logger.warning("marker_photo_not_found", image_path=image_path)
            return {"status": "failed", "error": "Photo file not found"}
        marker_url = build_public_url(path)
        return {
            "marker_path": str(path),
            "marker_url": marker_url,
            "metadata": {},
            "status": "ready",
        }

    def analyze_image_quality(self, image_path: str) -> dict:
        """Public wrapper for image quality analysis."""
        return self._analyze_image_quality(image_path)

    def build_image_recommendations(self, image_quality: dict) -> list[str]:
        """Build recommendations based on image quality metrics."""
        if not image_quality:
            return ["Не удалось проанализировать изображение — попробуйте другое фото"]

        recommendations: list[str] = []
        brightness = image_quality.get("brightness")
        contrast = image_quality.get("contrast")
        sharpness = image_quality.get("sharpness")
        edge_density = image_quality.get("edge_density")
        recognition_probability = image_quality.get("recognition_probability")

        if contrast is not None and contrast < self._MIN_CONTRAST:
            recommendations.append("Увеличьте контраст — детали должны быть более выраженными")
        if sharpness is not None and sharpness < self._MIN_SHARPNESS:
            recommendations.append("Сделайте фото резче — избегайте смаза")
        if brightness is not None and (brightness < 40 or brightness > 210):
            recommendations.append("Нормализуйте яркость — избегайте сильных пересветов и теней")
        if edge_density is not None and edge_density < 0.01:
            recommendations.append("Добавьте мелкие детали и текстуры по всей площади изображения")
        if recognition_probability is not None and recognition_probability < self._MIN_RECOGNITION_PROBABILITY:
            recommendations.append("Используйте изображение с более выраженными деталями и контрастом")

        if not recommendations:
            recommendations.append("Изображение выглядит подходящим для устойчивого трекинга")

        return recommendations

    def should_auto_enhance(self, image_quality: dict) -> bool:
        """Decide whether automatic enhancement should be applied."""
        if not image_quality:
            return False

        contrast = image_quality.get("contrast", 0.0)
        sharpness = image_quality.get("sharpness", 0.0)
        recognition_probability = image_quality.get("recognition_probability", 0.0)
        return (
            contrast < self._MIN_CONTRAST
            or sharpness < self._MIN_SHARPNESS
            or recognition_probability < self._MIN_RECOGNITION_PROBABILITY
        )

    def enhance_image_for_marker(self, image_path: str, output_path: str) -> Optional[str]:
        """
        Enhance image for better marker tracking (contrast + sharpness).

        Returns:
            Path to enhanced image or None if enhancement failed.
        """
        image = cv2.imread(str(image_path))
        if image is None:
            logger.warning("image_enhancement_failed", reason="read_failed", image_path=str(image_path))
            return None

        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l_channel)
        lab_enhanced = cv2.merge((l_enhanced, a_channel, b_channel))
        contrast_enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)

        gaussian = cv2.GaussianBlur(contrast_enhanced, (0, 0), 1.0)
        sharp_enhanced = cv2.addWeighted(contrast_enhanced, 1.6, gaussian, -0.6, 0)

        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output_path_obj), sharp_enhanced)
        logger.info("image_enhancement_applied", source=str(image_path), output=str(output_path_obj))
        return str(output_path_obj)

    def _analyze_image_quality(self, image_path: str) -> dict:
        """Compute basic image quality metrics for recognition estimation."""
        try:
            image = cv2.imread(str(image_path))
            if image is None:
                return {}

            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            brightness = float(np.mean(gray))
            contrast = float(np.std(gray))
            sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())

            edges = cv2.Canny(gray, 50, 150)
            edge_density = float(np.sum(edges > 0) / edges.size)

            recognition_probability = self._estimate_recognition_probability(
                contrast=contrast,
                brightness=brightness,
                sharpness=sharpness,
                edge_density=edge_density,
            )

            return {
                "brightness": brightness,
                "contrast": contrast,
                "sharpness": sharpness,
                "edge_density": edge_density,
                "recognition_probability": recognition_probability,
            }
        except Exception as exc:
            logger.warning("image_quality_analysis_failed", error=str(exc))
            return {}

    def _estimate_recognition_probability(
        self,
        contrast: float,
        brightness: float,
        sharpness: float,
        edge_density: float
    ) -> float:
        """Estimate recognition probability from image metrics."""
        contrast_score = min(1.0, contrast / self._CONTRAST_NORM)
        sharpness_score = min(1.0, sharpness / self._SHARPNESS_NORM)
        edge_score = min(1.0, edge_density / self._EDGE_DENSITY_TARGET)
        brightness_score = 1.0 - min(1.0, abs(brightness - 128.0) / 128.0)

        weighted_score = (
            0.35 * edge_score +
            0.25 * contrast_score +
            0.25 * sharpness_score +
            0.15 * brightness_score
        )

        return round(min(max(weighted_score, 0.0), 1.0), 4)

    # Removed save_marker - use generate_marker with storage_path instead

    async def validate_marker(self, marker_path: str) -> bool:
        """Validate marker image file (photo for ARCore tracking)."""
        path = Path(marker_path)
        if not path.exists():
            return False
        size = path.stat().st_size
        return 10_000 < size < 5_000_000  # 10KB - 5MB


# Singleton
marker_service = ARCoreMarkerService()
