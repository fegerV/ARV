import asyncio
from pathlib import Path
from typing import Optional
import structlog
from PIL import Image
import os

from app.core.config import settings
from app.core.storage import minio_client


logger = structlog.get_logger()


class ThumbnailService:
    """Сервис генерации превью изображений и видео"""

    def __init__(self):
        self.thumbnail_size = (320, 240)  # Ширина x Высота
        self.quality = 85  # Качество JPEG

    async def generate_image_thumbnail(
        self,
        image_path: str,
        output_dir: str = "storage/content/thumbnails",
        thumbnail_name: Optional[str] = None,
    ) -> dict:
        """
        Генерация превью для изображения
        
        Args:
            image_path: путь к исходному изображению
            output_dir: директория для сохранения превью
            thumbnail_name: имя файла превью (по умолчанию будет сгенерировано)
            
        Returns:
            dict с информацией о превью
        """
        log = logger.bind(image_path=image_path)
        log.info("image_thumbnail_generation_started")

        try:
            # Создаем директорию для превью
            thumb_dir = Path(output_dir)
            thumb_dir.mkdir(parents=True, exist_ok=True)

            # Определяем имя файла превью
            if not thumbnail_name:
                image_filename = Path(image_path).stem
                thumbnail_name = f"{image_filename}_thumb.jpg"

            # Путь к выходному файлу
            output_file = thumb_dir / thumbnail_name

            # Генерируем превью
            with Image.open(image_path) as img:
                # Преобразуем в RGB если нужно (для PNG с прозрачностью)
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Создаем превью с сохранением пропорций
                img.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)
                
                # Сохраняем превью
                img.save(output_file, 'JPEG', quality=self.quality, optimize=True)

            # Проверяем что файл создан
            if not output_file.exists():
                raise FileNotFoundError(f"Thumbnail file not created: {output_file}")

            # Для локального хранилища возвращаем локальный путь
            # В будущем можно добавить загрузку в различные типы хранилищ
            thumbnail_url = f"/storage/content/thumbnails/{thumbnail_name}"

            log.info(
                "image_thumbnail_generation_success",
                thumbnail_url=thumbnail_url,
                file_size=output_file.stat().st_size,
            )

            return {
                "thumbnail_path": str(output_file),
                "thumbnail_url": thumbnail_url,
                "status": "ready",
            }

        except Exception as e:
            log.error("image_thumbnail_generation_error", error=str(e), exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
            }

    async def generate_video_thumbnail(
        self,
        video_path: str,
        output_dir: str = "storage/content/thumbnails",
        thumbnail_name: Optional[str] = None,
        time_position: float = 1.0,  # секунда видео для создания превью
    ) -> dict:
        """
        Генерация превью для видео с помощью ffmpeg
        
        Args:
            video_path: путь к исходному видео
            output_dir: директория для сохранения превью
            thumbnail_name: имя файла превью (по умолчанию будет сгенерировано)
            time_position: время в секундах для захвата кадра
            
        Returns:
            dict с информацией о превью
        """
        log = logger.bind(video_path=video_path)
        log.info("video_thumbnail_generation_started")

        try:
            # Создаем директорию для превью
            thumb_dir = Path(output_dir)
            thumb_dir.mkdir(parents=True, exist_ok=True)

            # Определяем имя файла превью
            if not thumbnail_name:
                video_filename = Path(video_path).stem
                thumbnail_name = f"{video_filename}_thumb.jpg"

            # Путь к временному файлу кадра
            temp_frame = thumb_dir / f"{thumbnail_name}_temp.png"
            # Путь к выходному файлу
            output_file = thumb_dir / thumbnail_name

            # Извлекаем кадр из видео с помощью ffmpeg
            cmd = [
                "ffmpeg",
                "-ss", str(time_position),  # Позиция в видео
                "-i", video_path,  # Входной файл
                "-vframes", "1",  # Количество кадров
                "-f", "image2",  # Формат вывода
                str(temp_frame),  # Выходной файл
                "-y"  # Перезапись без запроса
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode()
                log.error("video_frame_extraction_failed", error=error_msg)
                raise RuntimeError(f"Video frame extraction failed: {error_msg}")

            # Проверяем что временный файл создан
            if not temp_frame.exists():
                raise FileNotFoundError(f"Temp frame file not created: {temp_frame}")

            # Создаем превью из извлеченного кадра
            with Image.open(temp_frame) as img:
                # Преобразуем в RGB если нужно
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Создаем превью с сохранением пропорций
                img.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)
                
                # Сохраняем превью
                img.save(output_file, 'JPEG', quality=self.quality, optimize=True)

            # Удаляем временный файл
            if temp_frame.exists():
                os.remove(temp_frame)

            # Проверяем что файл создан
            if not output_file.exists():
                raise FileNotFoundError(f"Thumbnail file not created: {output_file}")

            # Для локального хранилища возвращаем локальный путь
            # В будущем можно добавить загрузку в различные типы хранилищ
            thumbnail_url = f"/storage/content/thumbnails/{thumbnail_name}"

            log.info(
                "video_thumbnail_generation_success",
                thumbnail_url=thumbnail_url,
                file_size=output_file.stat().st_size,
            )

            return {
                "thumbnail_path": str(output_file),
                "thumbnail_url": thumbnail_url,
                "status": "ready",
            }

        except Exception as e:
            log.error("video_thumbnail_generation_error", error=str(e), exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
            }

    async def validate_thumbnail(self, thumbnail_path: str) -> bool:
        """Проверка валидности превью"""
        try:
            path = Path(thumbnail_path)
            if not path.exists():
                return False

            # Проверяем что файл является изображением
            with Image.open(path) as img:
                # Размер файла должен быть разумным (меньше 1MB)
                size = path.stat().st_size
                return 1000 < size < 1_000_000  # 1KB - 1MB
        except Exception:
            return False


# Singleton
thumbnail_service = ThumbnailService()