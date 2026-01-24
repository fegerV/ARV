from pathlib import Path
from typing import Optional
import structlog
import time
import cv2
import numpy as np

from app.core.config import settings
from app.core.storage import get_storage_provider_instance


logger = structlog.get_logger()


class MindARMarkerService:
    """Service for generating Mind AR markers"""

    _EDGE_DENSITY_TARGET = 0.2
    _CONTRAST_NORM = 50.0
    _SHARPNESS_NORM = 500.0

    async def generate_marker(
        self,
        ar_content_id: int,
        image_path: str,
        output_dir: str = "storage/markers",
    ) -> dict:
        """
        Generate Mind AR target file

        Args:
            ar_content_id: ID of AR content
            image_path: path to AR content image
            output_dir: directory for saving markers

        Returns:
            dict with marker information
        """
        log = logger.bind(ar_content_id=ar_content_id, image_path=image_path)
        log.info("mind_ar_generation_started")

        try:
            # Use the new MindAR generator
            from app.services.mindar_generator import mindar_generator
            start_time = time.time()
            result = await mindar_generator.generate_and_upload_marker(
                ar_content_id=str(ar_content_id),
                image_path=Path(image_path),
                max_features=settings.MINDAR_MAX_FEATURES
            )
            generation_time = time.time() - start_time
            
            if not result["success"]:
                log.error("mindar_generation_failed", error=result.get("error", "Unknown error"))
                return {
                    "status": "failed",
                    "error": result.get("error", "Unknown error"),
                }

            image_quality = self._analyze_image_quality(image_path)
            metadata = self._build_marker_metadata(result, generation_time, image_quality)
            marker_storage_path = result.get("storage_path") or result.get("marker_path")

            log.info(
                "mind_ar_generation_success",
                marker_url=result.get("marker_url"),
                file_size=result.get("file_size", 0),
                generation_time=generation_time,
            )

            return {
                "marker_path": marker_storage_path,
                "marker_url": result.get("marker_url"),
                "metadata": metadata,
                "status": "ready",
            }

        except Exception as e:
            log.error("mind_ar_generation_error", error=str(e), exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
            }

    async def _extract_marker_metadata(self, marker_file: Path) -> dict:
        """Extract metadata from .mind file"""
        try:
            # .mind file is binary format, read size
            file_size = marker_file.stat().st_size

            return {
                "file_size_bytes": file_size,
                "file_size_kb": round(file_size / 1024, 2),
                "format": "mind",
                "compiler_version": "1.2.5",
            }
        except Exception as e:
            logger.error("metadata_extraction_failed", error=str(e))
            return {}

    def _build_marker_metadata(self, result: dict, generation_time: float, image_quality: dict) -> dict:
        """Build marker metadata from generation result and image quality."""
        file_size_bytes = result.get("file_size")
        width = result.get("width")
        height = result.get("height")
        features_count = result.get("features")
        features_density = None
        if width and height and features_count is not None:
            features_density = float(features_count) / float(width * height)

        metadata = {
            "file_size_bytes": file_size_bytes,
            "file_size_kb": round(file_size_bytes / 1024, 2) if file_size_bytes else None,
            "format": "mind",
            "compiler_version": "1.2.5",
            "generation_time_seconds": round(generation_time, 4),
            "features_count": features_count,
            "features_density": round(features_density, 8) if features_density is not None else None,
            "width": width,
            "height": height,
            "image_quality": image_quality,
        }

        return metadata

    def analyze_image_quality(self, image_path: str) -> dict:
        """Public wrapper for image quality analysis."""
        return self._analyze_image_quality(image_path)

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

    def save_marker(self, project_id: int, marker_data: bytes) -> str:
        """Save generated marker file and return URL."""
        import tempfile
        import os
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mind") as temp_file:
            temp_file.write(marker_data)
            temp_path = temp_file.name
        
        try:
            # Save to storage using the provider
            storage_provider = get_storage_provider_instance()
            marker_storage_path = f"markers/marker_{project_id}.mind"
            
            # Use the async save_file method
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                url = loop.run_until_complete(
                    storage_provider.save_file(temp_path, marker_storage_path)
                )
                return url
            finally:
                loop.close()
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)

    async def validate_marker(self, marker_path: str) -> bool:
        """Validate marker file"""
        path = Path(marker_path)
        if not path.exists():
            return False

        # Mind AR files are usually 100-500KB
        size = path.stat().st_size
        return 10_000 < size < 5_000_000  # 10KB - 5MB


# Singleton
marker_service = MindARMarkerService()
