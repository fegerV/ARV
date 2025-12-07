import asyncio
from pathlib import Path
import asyncio
import subprocess
import structlog
from app.core.config import settings
from app.core.storage import storage_provider

log = structlog.get_logger()

class MindARMarkerService:
    """Сервис для генерации MindAR маркеров."""

    async def generate_marker(
        self,
        portrait_id: int,
        image_path: str,
        output_dir: str = "storage/markers",
    ) -> dict:
        """
        Генерация Mind AR target файла

        Args:
            portrait_id: ID портрета
            image_path: путь к изображению портрета
            output_dir: директория для сохранения маркеров

        Returns:
            dict с информацией о маркере
        """
        log = logger.bind(portrait_id=portrait_id, image_path=image_path)
        log.info("mind_ar_generation_started")

        # Создаем директорию для маркера
        marker_dir = Path(output_dir) / str(portrait_id)
        marker_dir.mkdir(parents=True, exist_ok=True)

        # Путь к выходному файлу
        output_file = marker_dir / "targets.mind"

        try:
            # Запускаем Mind AR compiler
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

            # Проверяем что файл создан
            if not output_file.exists():
                raise FileNotFoundError(f"Marker file not created: {output_file}")

            # Загружаем в хранилище или используем локальный путь
            marker_url = None
            if storage_provider:
                # Если провайдер хранения доступен, загружаем туда
                marker_url = await storage_provider.upload_file(
                    local_path=str(output_file),
                    remote_path=f"markers/{portrait_id}/targets.mind",
                    content_type="application/octet-stream",
                )
            else:
                # Если провайдер хранения недоступен, используем локальный путь
                marker_url = f"/storage/content/markers/{portrait_id}/targets.mind"
                # Убедимся, что директория существует
                marker_path = Path(settings.STORAGE_BASE_PATH) / "markers" / str(portrait_id)
                marker_path.mkdir(parents=True, exist_ok=True)
                # Копируем файл в нужное место
                import shutil
                shutil.copy2(output_file, marker_path / "targets.mind")

            # Получаем метаданные маркера
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
        """Извлечение метаданных из .mind файла"""
        try:
            # .mind файл это бинарный формат, читаем размер
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

    async def validate_marker(self, marker_path: str) -> bool:
        """Проверка валидности маркера"""
        path = Path(marker_path)
        if not path.exists():
            return False

        # Mind AR файлы обычно 100-500KB
        size = path.stat().st_size
        return 10_000 < size < 5_000_000  # 10KB - 5MB


# Singleton
marker_service = MindARMarkerService()
