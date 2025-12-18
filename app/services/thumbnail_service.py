import asyncio
from pathlib import Path
from typing import Optional
import structlog
from PIL import Image
import os
import tempfile
import time

from app.core.config import settings
from prometheus_client import Counter, Histogram


logger = structlog.get_logger()

# Prometheus metrics
THUMBNAIL_GENERATION_COUNT = Counter(
    'thumbnail_generation_total',
    'Total number of thumbnail generation attempts',
    ['type', 'status']
)

THUMBNAIL_GENERATION_DURATION = Histogram(
    'thumbnail_generation_duration_seconds',
    'Time spent generating thumbnails',
    ['type']
)

THUMBNAIL_UPLOAD_COUNT = Counter(
    'thumbnail_upload_total',
    'Total number of thumbnail uploads',
    ['provider', 'status']
)

THUMBNAIL_UPLOAD_DURATION = Histogram(
    'thumbnail_upload_duration_seconds',
    'Time spent uploading thumbnails',
    ['provider']
)

class ThumbnailService:
    """Сервис генерации превью изображений и видео"""

    def __init__(self):
        self.thumbnail_size = (320, 240)  # Ширина x Высота
        self.quality = 85  # Качество JPEG

    async def _save_thumbnail_with_provider(
        self,
        thumbnail_data: bytes,
        provider,
        remote_path: str,
        content_type: str = "image/jpeg"
    ) -> str:
        """Save thumbnail to storage using provider and return URL."""
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(thumbnail_data)
            temp_path = tmp_file.name
        
        try:
            # Record upload duration
            start_time = time.time()
            
            # Upload using provider
            url = await provider.upload_file(
                temp_path,
                remote_path,
                content_type
            )
            
            # Record metrics
            duration = time.time() - start_time
            provider_name = provider.__class__.__name__.replace('StorageProvider', '').lower()
            THUMBNAIL_UPLOAD_DURATION.labels(provider=provider_name).observe(duration)
            THUMBNAIL_UPLOAD_COUNT.labels(provider=provider_name, status='success').inc()
            
            return url
        except Exception as e:
            # Record failure metrics
            provider_name = provider.__class__.__name__.replace('StorageProvider', '').lower()
            THUMBNAIL_UPLOAD_COUNT.labels(provider=provider_name, status='failure').inc()
            raise
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)

    async def generate_image_thumbnail(
        self,
        image_path: str,
        output_dir: Optional[str] = None,
        thumbnail_name: Optional[str] = None,
        provider=None,
        company_id: Optional[int] = None
    ) -> dict:
        """
        Генерация превью для изображения
        
        Args:
            image_path: путь к исходному изображению
            output_dir: директория для сохранения превью
            thumbnail_name: имя файла превью (по умолчанию будет сгенерировано)
            provider: провайдер хранилища (опционально)
            company_id: ID компании для формирования пути в хранилище
            
        Returns:
            dict с информацией о превью
        """
        # Record generation duration
        start_time = time.time()
        
        log = logger.bind(image_path=image_path, company_id=company_id)
        log.info("image_thumbnail_generation_started")
        
        try:
            if output_dir is None:
                output_dir = str(Path(settings.MEDIA_ROOT) / "thumbnails")

            # Определяем имя файла превью
            if not thumbnail_name:
                image_filename = Path(image_path).stem
                thumbnail_name = f"{image_filename}_thumb.jpg"
            
            # Генерируем превью в памяти
            with Image.open(image_path) as img:
                # Преобразуем в RGB если нужно (для PNG с прозрачностью)
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Создаем превью с сохранением пропорций
                img.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)
                
                # Сохраняем превью в байты
                from io import BytesIO
                buffer = BytesIO()
                img.save(buffer, 'JPEG', quality=self.quality, optimize=True)
                thumbnail_data = buffer.getvalue()
            
            # Если предоставлен провайдер, загружаем через него
            if provider:
                # Формируем путь в хранилище
                storage_path = f"thumbnails/{company_id}/{thumbnail_name}" if company_id else f"thumbnails/{thumbnail_name}"
                thumbnail_url = await self._save_thumbnail_with_provider(
                    thumbnail_data,
                    provider,
                    storage_path,
                    "image/jpeg"
                )
                thumbnail_path = storage_path
            else:
                # Сохраняем локально
                thumb_dir = Path(output_dir)
                thumb_dir.mkdir(parents=True, exist_ok=True)
                output_file = thumb_dir / thumbnail_name
                
                with open(output_file, 'wb') as f:
                    f.write(thumbnail_data)
                
                # Проверяем что файл создан
                if not output_file.exists():
                    raise FileNotFoundError(f"Thumbnail file not created: {output_file}")
                
                thumbnail_path = str(output_file)
                thumbnail_url = f"/storage/thumbnails/{thumbnail_name}"
            
            # Record metrics
            duration = time.time() - start_time
            THUMBNAIL_GENERATION_DURATION.labels(type='image').observe(duration)
            THUMBNAIL_GENERATION_COUNT.labels(type='image', status='success').inc()
            
            log.info(
                "image_thumbnail_generation_success",
                thumbnail_url=thumbnail_url,
                thumbnail_path=thumbnail_path,
            )

            return {
                "thumbnail_path": thumbnail_path,
                "thumbnail_url": thumbnail_url,
                "status": "ready",
            }

        except Exception as e:
            # Record failure metrics
            duration = time.time() - start_time
            THUMBNAIL_GENERATION_DURATION.labels(type='image').observe(duration)
            THUMBNAIL_GENERATION_COUNT.labels(type='image', status='failure').inc()
            
            log.error("image_thumbnail_generation_error", error=str(e), exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
            }

    async def generate_video_thumbnail(
        self,
        video_path: str,
        output_dir: Optional[str] = None,
        thumbnail_name: Optional[str] = None,
        time_position: float = 1.0,  # секунда видео для создания превью
        provider=None,
        company_id: Optional[int] = None
    ) -> dict:
        """
        Генерация превью для видео с помощью ffmpeg
        
        Args:
            video_path: путь к исходному видео
            output_dir: директория для сохранения превью
            thumbnail_name: имя файла превью (по умолчанию будет сгенерировано)
            time_position: время в секундах для захвата кадра
            provider: провайдер хранилища (опционально)
            company_id: ID компании для формирования пути в хранилище
            
        Returns:
            dict с информацией о превью
        """
        # Record generation duration
        start_time = time.time()
        
        log = logger.bind(video_path=video_path, company_id=company_id)
        log.info("video_thumbnail_generation_started")

        try:
            if output_dir is None:
                output_dir = str(Path(settings.MEDIA_ROOT) / "thumbnails")

            # Определяем имя файла превью
            if not thumbnail_name:
                video_filename = Path(video_path).stem
                thumbnail_name = f"{video_filename}_thumb.jpg"

            # Путь к временному файлу кадра
            temp_frame_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            temp_frame = temp_frame_file.name
            temp_frame_file.close()  # Close but don't delete since we need the file
            
            # Извлекаем кадр из видео с помощью ffmpeg
            cmd = [
                "ffmpeg",
                "-ss", str(time_position),  # Позиция в видео
                "-i", video_path,  # Входной файл
                "-vframes", "1",  # Количество кадров
                "-f", "image2",  # Формат вывода
                temp_frame,  # Выходной файл
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
            if not os.path.exists(temp_frame):
                raise FileNotFoundError(f"Temp frame file not created: {temp_frame}")

            # Создаем превью из извлеченного кадра
            with Image.open(temp_frame) as img:
                # Преобразуем в RGB если нужно
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Создаем превью с сохранением пропорций
                img.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)
                
                # Сохраняем превью в байты
                from io import BytesIO
                buffer = BytesIO()
                img.save(buffer, 'JPEG', quality=self.quality, optimize=True)
                thumbnail_data = buffer.getvalue()

            # Удаляем временный файл
            if os.path.exists(temp_frame):
                os.remove(temp_frame)


            # Если предоставлен провайдер, загружаем через него
            if provider:
                # Формируем путь в хранилище
                storage_path = f"thumbnails/{company_id}/{thumbnail_name}" if company_id else f"thumbnails/{thumbnail_name}"
                thumbnail_url = await self._save_thumbnail_with_provider(
                    thumbnail_data,
                    provider,
                    storage_path,
                    "image/jpeg"
                )
                thumbnail_path = storage_path
            else:
                # Сохраняем локально
                thumb_dir = Path(output_dir)
                thumb_dir.mkdir(parents=True, exist_ok=True)
                output_file = thumb_dir / thumbnail_name
                
                with open(output_file, 'wb') as f:
                    f.write(thumbnail_data)
                
                # Проверяем что файл создан
                if not output_file.exists():
                    raise FileNotFoundError(f"Thumbnail file not created: {output_file}")
                
                thumbnail_path = str(output_file)
                thumbnail_url = f"/storage/thumbnails/{thumbnail_name}"

            # Record metrics
            duration = time.time() - start_time
            THUMBNAIL_GENERATION_DURATION.labels(type='video').observe(duration)
            THUMBNAIL_GENERATION_COUNT.labels(type='video', status='success').inc()

            log.info(
                "video_thumbnail_generation_success",
                thumbnail_url=thumbnail_url,
                thumbnail_path=thumbnail_path,
            )

            return {
                "thumbnail_path": thumbnail_path,
                "thumbnail_url": thumbnail_url,
                "status": "ready",
            }

        except Exception as e:
            # Record failure metrics
            duration = time.time() - start_time
            THUMBNAIL_GENERATION_DURATION.labels(type='video').observe(duration)
            THUMBNAIL_GENERATION_COUNT.labels(type='video', status='failure').inc()
            
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