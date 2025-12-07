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
from celery import Celery
from PIL import Image
import io
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.company import Company
from app.models.video import Video
from app.models.ar_content import ARContent
from app.models.storage import StorageConnection
from app.services.storage.factory import StorageProviderFactory

logger = structlog.get_logger()


# Размеры превью (16:9 соотношение)
THUMBNAIL_SIZES = {
    'small': (200, 112),   # Для списков/карточек
    'medium': (400, 225),  # Для детальных страниц
    'large': (800, 450)    # Для лайтбоксов/превью
}


celery_app = Celery(
    "app.tasks.thumbnail_generator",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)


@celery_app.task(bind=True, name="app.tasks.thumbnail_generator.generate_video_thumbnail")
def generate_video_thumbnail(self, video_id: int):
    """Generate thumbnail for a video."""
    async def _generate():
        async with AsyncSessionLocal() as db:
            try:
                # Get video
                video = await db.get(Video, video_id)
                if not video:
                    raise ValueError(f"Video {video_id} not found")
                
                # Get company and storage connection
                company = await db.get(Company, video.company_id)
                if not company or not company.storage_connection_id:
                    raise ValueError(f"Company {video.company_id} not found or has no storage connection")
                
                storage_conn = await db.get(StorageConnection, company.storage_connection_id)
                if not storage_conn:
                    raise ValueError(f"Storage connection {company.storage_connection_id} not found")
                
                # Create provider
                try:
                    provider = StorageProviderFactory.create_provider(
                        storage_conn.provider,
                        storage_conn.connection_metadata or {}
                    )
                except Exception as e:
                    logger.error(
                        "storage_provider_creation_failed",
                        company_id=company.id,
                        provider=storage_conn.provider,
                        error=str(e)
                    )
                    raise
                
                # Generate thumbnail
                try:
                    logger.info("Starting video thumbnail generation", video_id=video_id)
                    
                    # Download video from storage
                    video_data = await provider.download_file(video.video_path)
                    input_video = io.BytesIO(video_data)
                    
                    # Get video duration using FFmpeg probe
                    probe = ffmpeg.probe(input_video)
                    duration = float(probe['format']['duration'])
                    middle_time = duration / 2.0  # Take frame from middle
                    
                    logger.info("Extracting frame from video", 
                               video_id=video_id, 
                               duration=duration,
                               middle_time=middle_time)
                    
                    # Extract frame from middle of video
                    (
                        ffmpeg
                        .input(input_video, ss=middle_time)
                        .filter('scale', 1920, -1)  # 1920px width, auto height
                        .output('pipe:', vframes=1, format='rawvideo', pix_fmt='rgb24')
                        .overwrite_output()
                        .run(capture_stdout=True, capture_stderr=True)
                    )
                    
                    # Generate thumbnails in different sizes in WebP
                    thumbnails = {}
                    for size_name, (width, height) in THUMBNAIL_SIZES.items():
                        thumbnail_path = temp_dir / f"thumbnail_{size_name}.webp"
                        
                        # Resize + convert to WebP with optimization
                        img = Image.frombytes('RGB', (1920, 1080), output_frame)
                        
                        # Resize while maintaining aspect ratio
                        img.thumbnail((width, height), Image.Resampling.LANCZOS)
                        
                        # Save as WebP with optimization
                        img.save(thumbnail_path, 'WEBP', quality=85, method=6)
                    
                        # Upload to company storage
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
                    
                    # Update video record
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
                    # Clean up temporary files
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    
            except Exception as e:
                logger.error("thumbnail_generation_failed", video_id=video_id, error=str(e))
                raise self.retry(exc=e, countdown=60 * 2 ** self.request.retries)
                
    # Run async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_generate())
    finally:
        loop.close()


@celery_app.task(bind=True, name="app.tasks.thumbnail_generator.generate_image_thumbnail")
def generate_image_thumbnail(self, ar_content_id: int):
    """Generate thumbnail for an image."""
    async def _generate():
        async with AsyncSessionLocal() as db:
            try:
                # Get AR content
                ar_content = await db.get(ARContent, ar_content_id)
                if not ar_content:
                    raise ValueError(f"AR Content {ar_content_id} not found")
                
                # Get company and storage connection
                company = await db.get(Company, ar_content.company_id)
                if not company or not company.storage_connection_id:
                    raise ValueError(f"Company {ar_content.company_id} not found or has no storage connection")
                
                storage_conn = await db.get(StorageConnection, company.storage_connection_id)
                if not storage_conn:
                    raise ValueError(f"Storage connection {company.storage_connection_id} not found")
                
                # Create provider
                try:
                    provider = StorageProviderFactory.create_provider(
                        storage_conn.provider,
                        storage_conn.connection_metadata or {}
                    )
                except Exception as e:
                    logger.error(
                        "storage_provider_creation_failed",
                        company_id=company.id,
                        provider=storage_conn.provider,
                        error=str(e)
                    )
                    raise
                
                # Generate thumbnail
                try:
                    logger.info("Starting image thumbnail generation", ar_content_id=ar_content_id)
                    
                    # Download original from storage
                    image_data = await provider.download_file(ar_content.image_path)
                    input_image = io.BytesIO(image_data)
                    
                    thumbnails = {}
                    for size_name, (width, height) in THUMBNAIL_SIZES.items():
                        thumbnail_path = temp_dir / f"thumbnail_{size_name}.webp"
                        
                        with Image.open(input_image) as img:
                            # Convert to RGB if needed
                            if img.mode in ('RGBA', 'LA', 'P'):
                                background = Image.new('RGB', img.size, (255, 255, 255))
                                if img.mode == 'P':
                                    img = img.convert('RGBA')
                                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                                img = background
                            
                            # Maintain aspect ratio + center crop
                            img.thumbnail((width, height), Image.Resampling.LANCZOS)
                            
                            # Convert to WebP
                            img.save(thumbnail_path, 'WEBP', quality=85, method=6)
                        
                        # Upload to company storage
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
                    
                    # Update AR content record
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
                    
            except Exception as e:
                logger.error("thumbnail_generation_failed", ar_content_id=ar_content_id, error=str(e))
                raise self.retry(exc=e, countdown=60 * 2 ** self.request.retries)
                
    # Run async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_generate())
    finally:
        loop.close()


@celery_app.task(bind=True, name="app.tasks.thumbnail_generator.batch_generate_thumbnails")
def batch_generate_thumbnails(self, company_id: int):
    """Generate thumbnails for all videos of a company."""
    async def _generate():
        async with AsyncSessionLocal() as db:
            try:
                # Get company and storage connection
                company = await db.get(Company, company_id)
                if not company or not company.storage_connection_id:
                    raise ValueError(f"Company {company_id} not found or has no storage connection")
                
                storage_conn = await db.get(StorageConnection, company.storage_connection_id)
                if not storage_conn:
                    raise ValueError(f"Storage connection {company.storage_connection_id} not found")
                
                # Create provider
                try:
                    provider = StorageProviderFactory.create_provider(
                        storage_conn.provider,
                        storage_conn.connection_metadata or {}
                    )
                except Exception as e:
                    logger.error(
                        "storage_provider_creation_failed",
                        company_id=company.id,
                        provider=storage_conn.provider,
                        error=str(e)
                    )
                    raise
                
                # Generate thumbnails for all videos
                videos = await db.scalars(
                    select(Video).where(Video.company_id == company_id)
                ).all()
                for video in videos:
                    if not video.thumbnail_url:
                        generate_video_thumbnail.delay(video.id)
                
                logger.info("Batch thumbnail generation initiated", company_id=company_id)
                    
            except Exception as e:
                logger.error("batch_thumbnail_generation_failed", company_id=company_id, error=str(e))
                raise self.retry(exc=e, countdown=60 * 2 ** self.request.retries)
                
    # Run async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_generate())
    finally:
        loop.close()