from app.tasks.celery_app import celery_app
import structlog
from pathlib import Path
import asyncio
import subprocess
from typing import Optional

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.video import Video
from app.models.ar_content import ARContent
from app.models.company import Company
from app.models.storage import StorageConnection
from app.services.storage.factory import get_provider
from app.services.thumbnail_service import thumbnail_service

logger = structlog.get_logger()


@celery_app.task(bind=True, max_retries=3, name="app.tasks.preview_tasks.generate_video_thumbnail")
def generate_video_thumbnail(self, video_id: int):
    """
    Асинхронная генерация превью для видео
    """
    async def _generate():
        async with AsyncSessionLocal() as db:
            # Получаем видео
            video = await db.get(Video, video_id)
            if not video:
                raise ValueError(f"Video {video_id} not found")

            # Проверяем существование файла
            if not Path(video.video_path).exists():
                raise FileNotFoundError(f"Video file not found: {video.video_path}")

            # Получаем AR контент
            ar_content = await db.get(ARContent, video.ar_content_id)
            if not ar_content:
                raise ValueError(f"ARContent {video.ar_content_id} not found")

            # Получаем компанию и подключение к хранилищу
            company = await db.get(Company, ar_content.company_id)
            if not company:
                raise ValueError(f"Company {ar_content.company_id} not found")
            
            # Проверяем наличие подключения к хранилищу
            if not company.storage_connection_id:
                logger.warning("company_has_no_storage_connection", company_id=company.id)
                # Используем локальное хранилище по умолчанию
                result = await thumbnail_service.generate_video_thumbnail(
                    video_path=video.video_path,
                    thumbnail_name=f"video_{video.id}_thumb.jpg"
                )
            else:
                conn = await db.get(StorageConnection, company.storage_connection_id)
                if not conn:
                    raise ValueError(f"StorageConnection {company.storage_connection_id} not found")
                provider = get_provider(conn)
                
                # Используем наш сервис для генерации превью
                result = await thumbnail_service.generate_video_thumbnail(
                    video_path=video.video_path,
                    thumbnail_name=f"video_{video.id}_thumb.jpg"
                )

            try:
                if result["status"] == "ready":
                    # Обновляем запись в БД
                    video.thumbnail_url = result["thumbnail_url"]
                    await db.commit()

                    logger.info("video_thumbnail_generated", video_id=video_id, thumbnail_url=result["thumbnail_url"])
                    return {"video_id": video_id, "thumbnail_url": result["thumbnail_url"], "status": "success"}
                else:
                    raise RuntimeError(f"Thumbnail generation failed: {result.get('error')}")

            except Exception as e:
                logger.error("video_thumbnail_generation_failed", video_id=video_id, error=str(e))
                # Retry с exponential backoff
                raise self.retry(exc=e, countdown=60 * 2 ** self.request.retries)

    # Используем встроенный event loop для корректной работы с SQLAlchemy
    import asyncio
    try:
        # Пытаемся получить текущий event loop
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # Если event loop не существует, создаем новый
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(_generate())
    finally:
        # Не закрываем event loop, так как он может использоваться другими задачами
        pass


@celery_app.task(bind=True, max_retries=3, name="app.tasks.preview_tasks.generate_image_thumbnail")
def generate_image_thumbnail(self, ar_content_id: int):
    """
    Асинхронная генерация превью для изображения
    """
    async def _generate():
        async with AsyncSessionLocal() as db:
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
            
            # Проверяем наличие подключения к хранилищу
            if not company.storage_connection_id:
                logger.warning("company_has_no_storage_connection", company_id=company.id)
                # Используем локальное хранилище по умолчанию
                result = await thumbnail_service.generate_image_thumbnail(
                    image_path=ar_content.image_path,
                    thumbnail_name=f"image_{ar_content.id}_thumb.jpg"
                )
            else:
                conn = await db.get(StorageConnection, company.storage_connection_id)
                if not conn:
                    raise ValueError(f"StorageConnection {company.storage_connection_id} not found")
                provider = get_provider(conn)
                
                # Используем наш сервис для генерации превью
                result = await thumbnail_service.generate_image_thumbnail(
                    image_path=ar_content.image_path,
                    thumbnail_name=f"image_{ar_content.id}_thumb.jpg"
                )

            try:
                if result["status"] == "ready":
                    # Обновляем запись в БД
                    ar_content.thumbnail_url = result["thumbnail_url"]
                    await db.commit()

                    logger.info("image_thumbnail_generated", ar_content_id=ar_content_id, thumbnail_url=result["thumbnail_url"])
                    return {"ar_content_id": ar_content_id, "thumbnail_url": result["thumbnail_url"], "status": "success"}
                else:
                    raise RuntimeError(f"Thumbnail generation failed: {result.get('error')}")

            except Exception as e:
                logger.error("image_thumbnail_generation_failed", ar_content_id=ar_content_id, error=str(e))
                # Retry с exponential backoff
                raise self.retry(exc=e, countdown=60 * 2 ** self.request.retries)

    # Используем встроенный event loop для корректной работы с SQLAlchemy
    import asyncio
    try:
        # Пытаемся получить текущий event loop
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # Если event loop не существует, создаем новый
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(_generate())
    finally:
        # Не закрываем event loop, так как он может использоваться другими задачами
        pass