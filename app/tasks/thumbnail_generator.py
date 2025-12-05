"""
Celery tasks для генерации превью изображений и видео.
Использует FFmpeg для видео и Pillow для изображений.
Генерирует WebP превью в трёх размерах: small, medium, large.
"""
import asyncio
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Dict

import ffmpeg
import structlog
from celery import shared_task
from PIL import Image

from app.core.database import AsyncSessionLocal
from app.models.ar_content import ARContent
from app.models.company import Company
from app.models.video import Video
from app.core.storage import storage_manager

logger = structlog.get_logger()


# Размеры превью (16:9 соотношение)
THUMBNAIL_SIZES = {
    'small': (200, 112),   # Для списков/карточек
    'medium': (400, 225),  # Для детальных страниц
    'large': (800, 450)    # Для лайтбоксов/превью
}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_video_thumbnail(self, video_id: int):
    """
    Генерация превью из середины видео (WebP формат).
    
    Args:
        video_id: ID видео из таблицы videos
        
    Returns:
        dict: Словарь с URL превью разных размеров
        
    Raises:
        ValueError: Если видео не найдено
        ffmpeg.Error: Если FFmpeg не может обработать видео
    """
    async def task_logic():
        async with AsyncSessionLocal() as db:
            video = await db.get(Video, video_id)
            if not video:
                raise ValueError(f"Video {video_id} not found")
            
            # Получаем AR контент и компанию
            ar_content = await db.get(ARContent, video.ar_content_id)
            if not ar_content:
                raise ValueError(f"AR Content {video.ar_content_id} not found")
                
            company = await db.get(Company, ar_content.company_id)
            if not company:
                raise ValueError(f"Company {ar_content.company_id} not found")
            
            provider = storage_manager.get_provider(company.storage_connection)
            
            # Создаём временную директорию
            temp_dir = Path(tempfile.mkdtemp())
            input_video = temp_dir / "input.mp4"
            output_frame = temp_dir / "frame.png"
            
            try:
                logger.info("Starting video thumbnail generation", video_id=video_id)
                
                # Скачиваем видео из хранилища
                await provider.download_file(video.video_path, str(input_video))
                
                # Получаем длительность видео через FFmpeg probe
                probe = ffmpeg.probe(str(input_video))
                duration = float(probe['format']['duration'])
                middle_time = duration / 2.0  # Берём кадр из середины
                
                logger.info("Extracting frame from video", 
                           video_id=video_id, 
                           duration=duration,
                           middle_time=middle_time)
                
                # Извлекаем кадр из середины видео
                (
                    ffmpeg
                    .input(str(input_video), ss=middle_time)
                    .filter('scale', 1920, -1)  # 1920px ширина, авто высота
                    .output(str(output_frame), vframes=1)
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
                
                # Генерируем превью разных размеров в WebP
                thumbnails = {}
                for size_name, (width, height) in THUMBNAIL_SIZES.items():
                    thumbnail_path = temp_dir / f"thumbnail_{size_name}.webp"
                    
                    # Resize + конвертация в WebP с оптимизацией
                    with Image.open(output_frame) as img:
                        # Создаём копию в RGB (WebP требует RGB)
                        if img.mode in ('RGBA', 'LA', 'P'):
                            background = Image.new('RGB', img.size, (255, 255, 255))
                            if img.mode == 'P':
                                img = img.convert('RGBA')
                            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                            img = background
                        
                        # Resize с сохранением пропорций
                        img.thumbnail((width, height), Image.Resampling.LANCZOS)
                        
                        # Сохраняем в WebP с оптимизацией
                        img.save(thumbnail_path, 'WEBP', quality=85, method=6)
                    
                    # Загружаем в хранилище компании
                    storage_path = f"thumbnails/videos/{video.id}/{uuid.uuid4()}_{size_name}.webp"
                    thumbnail_url = await provider.upload_file(
                        str(thumbnail_path),
                        storage_path,
                        content_type='image/webp'
                    )
                    
                    thumbnails[size_name] = thumbnail_url
                    logger.info("Generated thumbnail", 
                               video_id=video_id, 
                               size=size_name, 
                               url=thumbnail_url)
                
                # Обновляем запись видео
                video.thumbnail_url = thumbnails['medium']
                video.thumbnail_small_url = thumbnails.get('small')
                video.thumbnail_large_url = thumbnails.get('large')
                await db.commit()
                
                logger.info("Video thumbnails generated successfully", 
                           video_id=video_id, 
                           thumbnails=thumbnails)
                return thumbnails
                
            except ffmpeg.Error as e:
                error_msg = e.stderr.decode() if e.stderr else str(e)
                logger.error("FFmpeg error during thumbnail generation", 
                            video_id=video_id, 
                            error=error_msg)
                raise
            except Exception as e:
                logger.error("Unexpected error during thumbnail generation", 
                            video_id=video_id, 
                            error=str(e))
                raise
            finally:
                # Очистка временных файлов
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    # Запуск async кода внутри Celery (sync context)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(task_logic())
    except Exception as exc:
        logger.error("Retrying thumbnail generation", video_id=video_id, attempt=self.request.retries)
        self.retry(exc=exc, countdown=60)
    finally:
        loop.close()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_image_thumbnail(self, ar_content_id: int):
    """
    Генерация превью для портрета/изображения (WebP формат).
    
    Args:
        ar_content_id: ID AR контента из таблицы ar_content
        
    Returns:
        dict: Словарь с URL превью разных размеров
        
    Raises:
        ValueError: Если AR контент не найден
    """
    async def task_logic():
        async with AsyncSessionLocal() as db:
            ar_content = await db.get(ARContent, ar_content_id)
            if not ar_content:
                raise ValueError(f"AR Content {ar_content_id} not found")
            
            company = await db.get(Company, ar_content.company_id)
            if not company:
                raise ValueError(f"Company {ar_content.company_id} not found")
                
            provider = storage_manager.get_provider(company.storage_connection)
            
            temp_dir = Path(tempfile.mkdtemp())
            input_image = temp_dir / "portrait.jpg"
            
            try:
                logger.info("Starting image thumbnail generation", ar_content_id=ar_content_id)
                
                # Скачиваем оригинал из хранилища
                await provider.download_file(ar_content.image_path, str(input_image))
                
                thumbnails = {}
                for size_name, (width, height) in THUMBNAIL_SIZES.items():
                    thumbnail_path = temp_dir / f"thumbnail_{size_name}.webp"
                    
                    with Image.open(input_image) as img:
                        # Конвертация в RGB если нужно
                        if img.mode in ('RGBA', 'LA', 'P'):
                            background = Image.new('RGB', img.size, (255, 255, 255))
                            if img.mode == 'P':
                                img = img.convert('RGBA')
                            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                            img = background
                        
                        # Сохраняем пропорции + обрезка по центру
                        img.thumbnail((width, height), Image.Resampling.LANCZOS)
                        
                        # Конвертация в WebP
                        img.save(thumbnail_path, 'WEBP', quality=85, method=6)
                    
                    # Загружаем в хранилище компании
                    storage_path = f"thumbnails/portraits/{ar_content.id}/{uuid.uuid4()}_{size_name}.webp"
                    thumbnail_url = await provider.upload_file(
                        str(thumbnail_path),
                        storage_path,
                        content_type='image/webp'
                    )
                    
                    thumbnails[size_name] = thumbnail_url
                    logger.info("Generated thumbnail", 
                               ar_content_id=ar_content_id, 
                               size=size_name, 
                               url=thumbnail_url)
                
                # Обновляем запись AR контента
                ar_content.thumbnail_url = thumbnails['medium']
                await db.commit()
                
                logger.info("Image thumbnails generated successfully", 
                           ar_content_id=ar_content_id, 
                           thumbnails=thumbnails)
                return thumbnails
                
            except Exception as e:
                logger.error("Error during image thumbnail generation", 
                            ar_content_id=ar_content_id, 
                            error=str(e))
                raise
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(task_logic())
    except Exception as exc:
        logger.error("Retrying thumbnail generation", ar_content_id=ar_content_id, attempt=self.request.retries)
        self.retry(exc=exc, countdown=60)
    finally:
        loop.close()
