from pathlib import Path
from typing import Optional
import structlog
import cv2
import numpy as np


# Minimum quality score threshold for "ready" status
MIN_MARKER_QUALITY_SCORE = 40


logger = structlog.get_logger()


class ImageQualityAnalyzer:
    """
    Image quality analyzer for AR content markers.
    
    Uses the photo image as the tracking target (raster JPEG/PNG).
    Analyzes image quality for ARCore marker suitability.
    """

    _EDGE_DENSITY_TARGET = 0.2
    _CONTRAST_NORM = 50.0
    _SHARPNESS_NORM = 500.0
    _MIN_CONTRAST = 35.0
    _MIN_SHARPNESS = 60.0
    _MIN_RECOGNITION_PROBABILITY = 0.6

    def analyze_image_quality(self, image_path: str) -> dict:
        """Public wrapper for image quality analysis."""
        return self._analyze_image_quality(image_path)

    def calculate_quality_score(self, metrics: dict) -> int:
        """Calculate overall quality score (0-100) from image metrics.
        
        Args:
            metrics: Dictionary with brightness, contrast, sharpness, edge_density
            
        Returns:
            Quality score from 0 to 100
        """
        if not metrics:
            return 0
        
        contrast = metrics.get("contrast", 0.0)
        sharpness = metrics.get("sharpness", 0.0)
        edge_density = metrics.get("edge_density", 0.0)
        brightness = metrics.get("brightness", 128.0)
        
        # Normalize each metric to 0-100 scale
        contrast_score = min(100.0, (contrast / self._CONTRAST_NORM) * 100)
        sharpness_score = min(100.0, (sharpness / self._SHARPNESS_NORM) * 100)
        edge_score = min(100.0, (edge_density / self._EDGE_DENSITY_TARGET) * 100)
        
        # Brightness score: optimal is around 128 (middle gray)
        brightness_deviation = abs(brightness - 128.0)
        brightness_score = max(0.0, 100.0 - (brightness_deviation / 128.0 * 100))
        
        # Weighted average
        quality_score = (
            0.30 * edge_score +
            0.30 * contrast_score +
            0.25 * sharpness_score +
            0.15 * brightness_score
        )
        
        return int(round(min(max(quality_score, 0.0), 100.0)))

    def get_marker_status(self, quality_score: int) -> str:
        """Determine marker status based on quality score.
        
        Args:
            quality_score: Quality score from 0-100
            
        Returns:
            "ready" if score >= MIN_MARKER_QUALITY_SCORE, else "low_quality"
        """
        if quality_score >= MIN_MARKER_QUALITY_SCORE:
            return "ready"
        return "low_quality"

    def get_quality_issue_reason(self, metrics: dict, quality_score: int) -> Optional[str]:
        """Get human-readable reason for low quality score.
        
        Args:
            metrics: Image metrics dictionary
            quality_score: Calculated quality score
            
        Returns:
            Reason string or None if quality is good
        """
        if quality_score >= MIN_MARKER_QUALITY_SCORE:
            return None
        
        issues = []
        contrast = metrics.get("contrast", 0.0)
        sharpness = metrics.get("sharpness", 0.0)
        edge_density = metrics.get("edge_density", 0.0)
        brightness = metrics.get("brightness", 128.0)
        
        if contrast < self._MIN_CONTRAST:
            issues.append("низкий контраст")
        if sharpness < self._MIN_SHARPNESS:
            issues.append("низкая резкость")
        if edge_density < 0.01:
            issues.append("мало деталей/текстур")
        if brightness < 40 or brightness > 210:
            issues.append("проблемы с яркостью")
        
        if issues:
            return "Проблемы качества: " + ", ".join(issues)
        return "Низкое общее качество изображения"

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

    @staticmethod
    def get_quality_level(recognition_probability: float | None) -> str:
        """Classify recognition probability into a human-readable quality level.

        Returns:
            ``"good"``  — probability >= 0.6 (reliable tracking)
            ``"fair"``  — probability >= 0.35 (may be unstable)
            ``"poor"``  — probability < 0.35 (high risk of failure)
            ``"unknown"`` — probability is ``None``
        """
        if recognition_probability is None:
            return "unknown"
        if recognition_probability >= 0.6:
            return "good"
        if recognition_probability >= 0.35:
            return "fair"
        return "poor"

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


# Singleton
image_quality_analyzer = ImageQualityAnalyzer()
