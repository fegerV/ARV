from app.tasks.celery_app import celery_app
import structlog
from pathlib import Path
from datetime import datetime
import asyncio

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.ar_content import ARContent
from app.models.portrait import Portrait
from app.models.company import Company
from app.models.storage import StorageConnection
from app.services.storage.factory import get_provider

logger = structlog.get_logger()


@celery_app.task(name="app.tasks.marker_tasks.generate_ar_marker", bind=True)
def generate_ar_marker(self, ar_content_id: str):
    """
    Generate Mind AR marker file (.mind) from portrait image.
    
    Args:
        ar_content_id: UUID of AR content
        
    Returns:
        dict: Task result with marker file path
    """
    logger.info("marker_generation_started", ar_content_id=ar_content_id, task_id=self.request.id)
    
    # TODO: Implement Mind AR marker generation
    # This will be implemented in Phase 3
    
    logger.info("marker_generation_completed", ar_content_id=ar_content_id)
    
    return {"status": "completed", "ar_content_id": ar_content_id}


@celery_app.task(bind=True, max_retries=3, name="app.tasks.marker_tasks.generate_mind_marker_task")
def generate_mind_marker_task(self, portrait_id: int):
    """
    Асинхронная генерация Mind AR маркера
    """
    async def _generate():
        async with AsyncSessionLocal() as db:
            # Получаем портрет
            portrait = await db.get(Portrait, portrait_id)
            if not portrait:
                raise ValueError(f"Portrait {portrait_id} not found")

            # Обновляем статус
            portrait.marker_status = "processing"
            await db.commit()

            try:
                # Генерируем маркер
                result = await marker_service.generate_marker(
                    portrait_id=portrait.id,
                    image_path=portrait.image_path,
                )

                # Сохраняем результат в БД
                portrait.marker_path = result["marker_path"]
                portrait.marker_url = result["marker_url"]
                portrait.marker_status = result["status"]
                portrait.portrait_metadata = result.get("metadata", {})

                await db.commit()

                return {
                    "portrait_id": portrait_id,
                    "marker_url": result["marker_url"],
                    "status": "success",
                }

            except Exception as e:
                portrait.marker_status = "failed"
                await db.commit()

                # Retry с exponential backoff
                raise self.retry(exc=e, countdown=60 * 2 ** self.request.retries)

    # Запускаем async функцию в новом event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_generate())
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, name="app.tasks.marker_tasks.generate_ar_content_marker_task")
def generate_ar_content_marker_task(self, content_id: int):
    async def _generate():
        async with AsyncSessionLocal() as db:
            ac = await db.get(ARContent, content_id)
            if not ac:
                raise ValueError(f"ARContent {content_id} not found")

            # Load company and storage connection
            company = await db.get(Company, ac.company_id)
            if not company:
                raise ValueError(f"Company {ac.company_id} not found")
            conn = await db.get(StorageConnection, company.storage_connection_id)
            if not conn:
                raise ValueError(f"StorageConnection {company.storage_connection_id} not found")
            provider = get_provider(conn)

            # Update status to processing
            ac.marker_status = "processing"
            await db.commit()

            base_path = (company.storage_path or "/").rstrip("/")
            portraits_folder = f"{base_path}/portraits/original_images"
            markers_folder = f"{base_path}/markers/mindar_targets"

            # Ensure folders exist
            for folder in [portraits_folder, markers_folder, f"{base_path}/videos", f"{base_path}/qr-codes", f"{base_path}/thumbnails"]:
                try:
                    await provider.create_folder(folder)
                except Exception:
                    pass

            # Upload original image into storage (optional if not already uploaded)
            image_name = Path(ac.image_path).name
            image_remote_path = f"{portraits_folder}/{image_name}"
            try:
                await provider.upload_file(file_path=ac.image_path, destination_path=image_remote_path)
            except Exception:
                # ignore if fails; continue marker generation
                pass

            # Generate MindAR marker using compiler
            out_dir = Path("/tmp/mindar_markers") / str(ac.id)
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / "targets.mind"

            proc = await asyncio.create_subprocess_exec(
                "npx", "mind-ar-js-compiler",
                "--input", ac.image_path,
                "--output", str(out_file),
                "--max-features", str(getattr(settings, "MINDAR_MAX_FEATURES", 800)),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0 or not out_file.exists():
                raise RuntimeError(f"Mind AR compilation failed: {stderr.decode()}")

            # Upload .mind to storage
            mind_remote_path = f"{markers_folder}/{str(ac.unique_id)}.mind"
            marker_url = await provider.upload_file(
                file_path=str(out_file),
                destination_path=mind_remote_path,
                content_type="application/octet-stream",
            )

            # Update DB
            ac.marker_path = mind_remote_path
            ac.marker_url = marker_url
            ac.marker_status = "ready"
            ac.marker_generated_at = datetime.utcnow()
            await db.commit()

            return {"content_id": content_id, "marker_url": marker_url, "status": "success"}

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_generate())
    finally:
        loop.close()
