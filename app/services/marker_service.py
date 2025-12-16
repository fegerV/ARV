import asyncio
from pathlib import Path
from typing import Optional
import structlog

from app.core.config import settings
from app.core.storage import get_storage_provider_instance


logger = structlog.get_logger()


class MindARMarkerService:
    """Service for generating Mind AR markers"""

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

        # Create directory for marker
        marker_dir = Path(output_dir) / str(ar_content_id)
        marker_dir.mkdir(parents=True, exist_ok=True)

        # Path to output file
        output_file = marker_dir / "targets.mind"

        try:
            # Run Mind AR compiler
            cmd = [
                "npx",
                "mind-ar-js-compiler",
                "--input",
                image_path,
                "--output",
                str(output_file),
                "--max-features",
                str(settings.MINDAR_MAX_FEATURES),
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode()
                log.error("mind_ar_compilation_failed", error=error_msg)
                raise RuntimeError(f"Mind AR compilation failed: {error_msg}")

            # Check that file was created
            if not output_file.exists():
                raise FileNotFoundError(f"Marker file not created: {output_file}")

            # Upload to storage
            storage_provider = get_storage_provider_instance()
            marker_storage_path = f"markers/{ar_content_id}/targets.mind"
            marker_url = await storage_provider.save_file(
                source_path=str(output_file),
                destination_path=marker_storage_path
            )

            # Get marker metadata
            metadata = await self._extract_marker_metadata(output_file)

            log.info(
                "mind_ar_generation_success",
                marker_url=marker_url,
                file_size=output_file.stat().st_size,
            )

            return {
                "marker_path": str(output_file),
                "marker_url": marker_url,
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