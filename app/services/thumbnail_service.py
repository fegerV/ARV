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
        # Multiple thumbnail sizes for different use cases
        self.thumbnail_sizes = {
            'small': (150, 112),    # For lists
            'medium': (320, 240),   # Standard
            'large': (640, 480),    # For lightbox
        }
        self.default_size = 'medium'
        self.quality = 90  # Higher quality for WebP

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
        except Exception:
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
        storage_path: Path,
        thumbnail_name: Optional[str] = None,
        output_dir: Optional[str] = None,  # Deprecated, kept for compatibility
        provider=None,  # Deprecated, kept for compatibility
        company_id: Optional[int] = None,  # Deprecated, kept for compatibility
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
            # Генерируем превью в разных размерах
            if not storage_path:
                raise ValueError("storage_path is required for thumbnail generation")
            
            storage_path.mkdir(parents=True, exist_ok=True)
            
            # Generate thumbnails in all sizes
            generated_thumbnails = {}
            with Image.open(image_path) as img:
                # Преобразуем в RGB если нужно (для PNG с прозрачностью)
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Create white background for transparent images
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    if img.mode == 'RGBA':
                        background.paste(img, mask=img.split()[-1])
                    img = background
                elif img.mode not in ('RGB', 'L'):
                    img = img.convert('RGB')
                
                # Generate each size
                for size_name, size_dimensions in self.thumbnail_sizes.items():
                    # Create a copy for this size
                    thumb_img = img.copy()
                    
                    # Resize with high quality resampling
                    thumb_img.thumbnail(size_dimensions, Image.Resampling.LANCZOS)
                    
                    # Save to bytes
                    from io import BytesIO
                    buffer = BytesIO()
                    thumb_img.save(buffer, 'WEBP', quality=self.quality, method=6)
                    thumbnail_data = buffer.getvalue()
                    
                    # Save to file
                    thumbnail_filename = f"thumbnail_{size_name}.webp" if size_name != self.default_size else "thumbnail.webp"
                    thumbnail_file_path = storage_path / thumbnail_filename
                    
                    with open(thumbnail_file_path, 'wb') as f:
                        f.write(thumbnail_data)
                    
                    # Build URL for this thumbnail
                    from app.utils.ar_content import build_public_url
                    thumbnail_url = build_public_url(thumbnail_file_path)
                    generated_thumbnails[size_name] = {
                        'url': thumbnail_url,
                        'path': str(thumbnail_file_path),
                        'size': size_dimensions
                    }
            
            # Use medium (default) thumbnail as main thumbnail
            thumbnail_file_path = storage_path / "thumbnail.webp"
            thumbnail_path = str(thumbnail_file_path)
            thumbnail_url = generated_thumbnails[self.default_size]['url']
            
            # Проверяем что файл создан
            if not thumbnail_file_path.exists():
                raise FileNotFoundError(f"Thumbnail file not created: {thumbnail_file_path}")
            
            # Record metrics
            duration = time.time() - start_time
            THUMBNAIL_GENERATION_DURATION.labels(type='image').observe(duration)
            THUMBNAIL_GENERATION_COUNT.labels(type='image', status='success').inc()
            
            log.info(
                "image_thumbnail_generation_success",
                thumbnail_url=thumbnail_url,
                thumbnail_path=thumbnail_path,
                sizes_generated=list(generated_thumbnails.keys()),
            )

            return {
                "thumbnail_path": thumbnail_path,
                "thumbnail_url": thumbnail_url,
                "status": "ready",
                "thumbnails": generated_thumbnails,  # All sizes available
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

    def _derive_size_name(self, base_name: str, size_label: str) -> str:
        """Формирует имя файла для конкретного размера превью.

        Пример: ``video_1_thumb.webp`` → ``video_1_thumb_small.webp``
        """
        stem = Path(base_name).stem
        return f"{stem}_{size_label}.webp"

    async def _extract_video_frame(
        self,
        video_path: str,
        time_position: float,
    ) -> str:
        """Извлекает один кадр из видео через ffmpeg.

        Returns:
            Путь к временному PNG-файлу с кадром.

        Raises:
            RuntimeError: если ffmpeg вернул ненулевой код.
            FileNotFoundError: если временный файл не был создан.
        """
        temp_frame_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        temp_frame = temp_frame_file.name
        temp_frame_file.close()

        cmd = [
            "ffmpeg",
            "-ss", str(time_position),
            "-i", video_path,
            "-vframes", "1",
            "-f", "image2",
            temp_frame,
            "-y",
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode()
            raise RuntimeError(f"Video frame extraction failed: {error_msg}")

        if not os.path.exists(temp_frame):
            raise FileNotFoundError(f"Temp frame file not created: {temp_frame}")

        return temp_frame

    async def generate_video_thumbnail(
        self,
        video_path: str,
        output_dir: Optional[str] = None,
        thumbnail_name: Optional[str] = None,
        time_position: float = 1.0,
        provider=None,
        company_id: Optional[int] = None,
    ) -> dict:
        """Генерация пропорциональных WebP-превью для видео в 3 размерах.

        Создаёт ``small``, ``medium`` и ``large`` превью из одного кадра,
        извлечённого с помощью ffmpeg.

        Args:
            video_path: путь к исходному видео.
            output_dir: директория для сохранения превью.
            thumbnail_name: базовое имя файла превью.
            time_position: секунда видео для захвата кадра.
            provider: провайдер хранилища (опционально).
            company_id: ID компании для формирования пути в хранилище.

        Returns:
            dict с полями ``status``, ``thumbnail_path``, ``thumbnail_url``,
            ``thumbnails`` (все размеры).
        """
        start_time = time.time()

        log = logger.bind(video_path=video_path, company_id=company_id)
        log.info("video_thumbnail_generation_started")

        try:
            if output_dir is None:
                # Thumbnails are served via /storage/ which is mounted from
                # STORAGE_BASE_PATH.  Saving under MEDIA_ROOT (a different
                # directory on most servers) would cause 404s.
                output_dir = str(
                    Path(settings.STORAGE_BASE_PATH).resolve() / "thumbnails"
                )

            if not thumbnail_name:
                video_filename = Path(video_path).stem
                thumbnail_name = f"{video_filename}_thumb.webp"

            # --- Извлекаем кадр из видео ---
            temp_frame = await self._extract_video_frame(video_path, time_position)

            try:
                generated = {}

                with Image.open(temp_frame) as img:
                    if img.mode in ("RGBA", "LA", "P"):
                        img = img.convert("RGB")

                    # Генерируем превью для каждого размера
                    for size_label, dimensions in self.thumbnail_sizes.items():
                        thumb = img.copy()
                        thumb.thumbnail(dimensions, Image.Resampling.LANCZOS)

                        from io import BytesIO
                        buf = BytesIO()
                        thumb.save(buf, "WEBP", quality=self.quality, method=6)
                        data = buf.getvalue()

                        size_filename = self._derive_size_name(thumbnail_name, size_label)

                        if provider:
                            prefix = f"thumbnails/{company_id}" if company_id else "thumbnails"
                            remote_path = f"{prefix}/{size_filename}"
                            url = await self._save_thumbnail_with_provider(
                                data, provider, remote_path, "image/webp",
                            )
                            generated[size_label] = {
                                "path": remote_path,
                                "url": url,
                                "size": dimensions,
                            }
                        else:
                            thumb_dir = Path(output_dir)
                            thumb_dir.mkdir(parents=True, exist_ok=True)
                            out_file = thumb_dir / size_filename

                            with open(out_file, "wb") as f:
                                f.write(data)

                            if not out_file.exists():
                                raise FileNotFoundError(
                                    f"Thumbnail file not created: {out_file}"
                                )

                            generated[size_label] = {
                                "path": str(out_file),
                                "url": f"/storage/thumbnails/{size_filename}",
                                "size": dimensions,
                            }
            finally:
                # Удаляем временный файл кадра в любом случае
                if os.path.exists(temp_frame):
                    os.remove(temp_frame)

            # Основной thumbnail — medium
            main = generated[self.default_size]

            # Record metrics
            duration = time.time() - start_time
            THUMBNAIL_GENERATION_DURATION.labels(type="video").observe(duration)
            THUMBNAIL_GENERATION_COUNT.labels(type="video", status="success").inc()

            log.info(
                "video_thumbnail_generation_success",
                thumbnail_url=main["url"],
                thumbnail_path=main["path"],
                sizes_generated=list(generated.keys()),
            )

            return {
                "thumbnail_path": main["path"],
                "thumbnail_url": main["url"],
                "status": "ready",
                "thumbnails": generated,
            }

        except Exception as e:
            duration = time.time() - start_time
            THUMBNAIL_GENERATION_DURATION.labels(type="video").observe(duration)
            THUMBNAIL_GENERATION_COUNT.labels(type="video", status="failure").inc()

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
            with Image.open(path):
                # Размер файла должен быть разумным (меньше 1MB)
                size = path.stat().st_size
                return 1000 < size < 1_000_000  # 1KB - 1MB
        except Exception:
            return False


# Singleton
thumbnail_service = ThumbnailService()