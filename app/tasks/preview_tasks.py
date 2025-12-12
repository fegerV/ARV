from app.tasks.celery_app import celery_app
import structlog
from pathlib import Path
import asyncio
import subprocess
from typing import Optional
from datetime import datetime

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.video import Video
from app.models.ar_content import ARContent
from app.models.company import Company
from app.models.storage import StorageConnection
from app.utils.ar_content import build_ar_content_storage_path, build_public_url
from app.utils.video_utils import get_video_middle_frame_time
from app.services.thumbnail_service import thumbnail_service
import time

# Prometheus metrics
from prometheus_client import Counter, Histogram

TASK_EXECUTION_COUNT = Counter(
    'thumbnail_task_execution_total',
    'Total number of thumbnail task executions',
    ['task_type', 'status']
)

TASK_EXECUTION_DURATION = Histogram(
    'thumbnail_task_execution_duration_seconds',
    'Time spent executing thumbnail tasks',
    ['task_type']
)

logger = structlog.get_logger()


@celery_app.task(bind=True, max_retries=3, name="app.tasks.preview_tasks.generate_video_thumbnail")
def generate_video_thumbnail(self, video_id: int):
    """
    Generate preview thumbnail from the middle frame of a video.
    """
    # Record task execution duration
    start_time = time.time()
    task_type = 'video'
    
    async def _generate():
        async with AsyncSessionLocal() as db:
            try:
                # Get video
                video = await db.get(Video, video_id)
                if not video:
                    raise ValueError(f"Video {video_id} not found")

                # Check if video file exists
                if not Path(video.video_path).exists():
                    raise FileNotFoundError(f"Video file not found: {video.video_path}")

                # Get AR content
                ar_content = await db.get(ARContent, video.ar_content_id)
                if not ar_content:
                    raise ValueError(f"ARContent {video.ar_content_id} not found")

                # Get company
                company = await db.get(Company, ar_content.company_id)
                if not company:
                    raise ValueError(f"Company {ar_content.company_id} not found")
                
                # Build storage paths
                storage_base_path = build_ar_content_storage_path(
                    ar_content.company_id,
                    ar_content.project_id,
                    ar_content.unique_id
                )
                previews_path = storage_base_path / "previews"
                
                # Get middle frame timestamp
                middle_time = await get_video_middle_frame_time(video.video_path)
                
                # Generate preview thumbnail
                result = await thumbnail_service.generate_video_thumbnail(
                    video_path=video.video_path,
                    output_dir=str(previews_path),
                    thumbnail_name=f"video_{video.id}_preview.jpg",
                    time_position=middle_time,
                    provider=None,  # Using local storage for now
                    company_id=company.id
                )

                if result["status"] == "ready":
                    # Update video record with preview URL
                    video.preview_url = result["thumbnail_url"]
                    video.status = "active"  # Mark as ready
                    video.updated_at = datetime.utcnow()
                    await db.commit()

                    logger.info(
                        "video_preview_generated", 
                        video_id=video_id, 
                        preview_url=result["thumbnail_url"],
                        middle_time=middle_time
                    )
                    TASK_EXECUTION_COUNT.labels(task_type=task_type, status='success').inc()
                    return {
                        "video_id": video_id, 
                        "preview_url": result["thumbnail_url"], 
                        "status": "success",
                        "middle_time": middle_time
                    }
                else:
                    raise RuntimeError(f"Preview generation failed: {result.get('error')}")

            except Exception as e:
                TASK_EXECUTION_COUNT.labels(task_type=task_type, status='failure').inc()
                logger.error("video_preview_generation_failed", video_id=video_id, error=str(e))
                # Retry with exponential backoff
                raise self.retry(exc=e, countdown=60 * 2 ** self.request.retries)

    # Record task duration
    try:
        # Используем встроенный event loop для корректной работы с SQLAlchemy
        import asyncio
        try:
            # Пытаемся получить текущий event loop
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # Если event loop не существует, создаем новый
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(_generate())
        
        # Record success metrics
        duration = time.time() - start_time
        TASK_EXECUTION_DURATION.labels(task_type=task_type).observe(duration)
        
        return result
    except Exception as e:
        # Record failure metrics
        duration = time.time() - start_time
        TASK_EXECUTION_DURATION.labels(task_type=task_type).observe(duration)
        TASK_EXECUTION_COUNT.labels(task_type=task_type, status='failure').inc()
        raise


@celery_app.task(bind=True, max_retries=3, name="app.tasks.preview_tasks.generate_image_thumbnail")
def generate_image_thumbnail(self, ar_content_id: int):
    """
    Асинхронная генерация превью для изображения
    """
    # Record task execution duration
    start_time = time.time()
    task_type = 'image'
    
    async def _generate():
        async with AsyncSessionLocal() as db:
            try:
                # Получаем AR контент
                ar_content = await db.get(ARContent, ar_content_id)
                if not ar_content:
                    raise ValueError(f"ARContent {ar_content_id} not found")

                # Проверяем существование файла
                if not Path(ar_content.image_path).exists():
                    raise FileNotFoundError(f"Image file not found: {ar_content.image_path}")

                # Получаем компанию и подключение к хранилищу
                company = await db.get(Company, ar_content.company_id)
                if not company:
                    raise ValueError(f"Company {ar_content.company_id} not found")
                
                # TODO: Implement when storage providers are ready
                # Инициализируем провайдер как None
                # provider = None
                
                # Проверяем наличие подключения к хранилищу
                # if company.storage_connection_id:
                #     conn = await db.get(StorageConnection, company.storage_connection_id)
                #     if not conn:
                #         logger.warning("storage_connection_not_found", company_id=company.id, storage_connection_id=company.storage_connection_id)
                #     else:
                #         try:
                #             provider = get_provider(conn)
                #             logger.info("storage_provider_initialized", company_id=company.id, provider_type=conn.provider)
                #         except Exception as e:
                #             logger.error("storage_provider_init_failed", company_id=company.id, error=str(e))
                # else:
                #     logger.warning("company_has_no_storage_connection", company_id=company.id)
                
                # Используем наш сервис для генерации превью
                result = await thumbnail_service.generate_image_thumbnail(
                    image_path=ar_content.image_path,
                    thumbnail_name=f"image_{ar_content.id}_thumb.jpg",
                    provider=provider,
                    company_id=company.id
                )

                if result["status"] == "ready":
                    # Обновляем запись в БД
                    ar_content.thumbnail_url = result["thumbnail_url"]
                    await db.commit()

                    logger.info("image_thumbnail_generated", ar_content_id=ar_content_id, thumbnail_url=result["thumbnail_url"])
                    TASK_EXECUTION_COUNT.labels(task_type=task_type, status='success').inc()
                    return {"ar_content_id": ar_content_id, "thumbnail_url": result["thumbnail_url"], "status": "success"}
                else:
                    raise RuntimeError(f"Thumbnail generation failed: {result.get('error')}")

            except Exception as e:
                TASK_EXECUTION_COUNT.labels(task_type=task_type, status='failure').inc()
                logger.error("image_thumbnail_generation_failed", ar_content_id=ar_content_id, error=str(e))
                # Retry с exponential backoff
                raise self.retry(exc=e, countdown=60 * 2 ** self.request.retries)

    # Record task duration
    try:
        # Используем встроенный event loop для корректной работы с SQLAlchemy
        import asyncio
        try:
            # Пытаемся получить текущий event loop
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # Если event loop не существует, создаем новый
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(_generate())
        
        # Record success metrics
        duration = time.time() - start_time
        TASK_EXECUTION_DURATION.labels(task_type=task_type).observe(duration)
        
        return result
    except Exception as e:
        # Record failure metrics
        duration = time.time() - start_time
        TASK_EXECUTION_DURATION.labels(task_type=task_type).observe(duration)
        TASK_EXECUTION_COUNT.labels(task_type=task_type, status='failure').inc()
        raise