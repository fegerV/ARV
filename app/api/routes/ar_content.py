from uuid import uuid4
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import aiofiles

from app.core.config import settings
from app.core.database import get_db
from app.models.ar_content import ARContent
from app.models.video import Video
from app.tasks.marker_tasks import generate_ar_content_marker_task
from app.tasks.thumbnail_generator import generate_video_thumbnail, generate_image_thumbnail

router = APIRouter()


def _build_public_url(saved: Path) -> str:
    base = Path(settings.STORAGE_BASE_PATH)
    rel = saved.relative_to(base)
    return f"/storage/{rel.as_posix()}"


@router.post("/ar-content")
async def create_ar_content(
    company_id: int = Form(...),
    project_id: int = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    uid = uuid4()
    content_dir = Path(settings.STORAGE_BASE_PATH) / "ar_content" / str(uid)
    content_dir.mkdir(parents=True, exist_ok=True)

    image_path = content_dir / image.filename
    async with aiofiles.open(image_path, "wb") as out:
        while True:
            chunk = await image.read(1024 * 1024)
            if not chunk:
                break
            await out.write(chunk)

    ac = ARContent(
        project_id=project_id,
        company_id=company_id,
        unique_id=uid,
        title=title,
        description=description,
        image_path=str(image_path),
        image_url=_build_public_url(image_path),
        marker_status="pending",
        is_active=True,
        metadata={},
    )
    db.add(ac)
    await db.flush()
    await db.commit()
    await db.refresh(ac)

    # Запускаем генерацию маркера и превью параллельно
    marker_task = generate_ar_content_marker_task.delay(ac.id)
    thumbnail_task = generate_image_thumbnail.delay(ac.id)

    return {
        "id": ac.id,
        "unique_id": str(ac.unique_id),
        "image_url": ac.image_url,
        "marker_status": ac.marker_status,
        "marker_task_id": marker_task.id,
        "thumbnail_task_id": thumbnail_task.id,
    }

@router.get("/projects/{project_id}/ar-content")
async def list_ar_content_for_project(project_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(ARContent).where(ARContent.project_id == project_id)
    res = await db.execute(stmt)
    items = []
    for ac in res.scalars().all():
        items.append({
            "id": ac.id,
            "unique_id": str(ac.unique_id),
            "title": ac.title,
            "marker_status": ac.marker_status,
            "image_url": ac.image_url,
        })
    return {"items": items}

    task = generate_ar_content_marker_task.delay(content_id)
    return {"task_id": task.id}


@router.post("/ar-content/{content_id}/videos")
async def upload_video(
    content_id: int,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    is_active: bool = Form(False),
    db: AsyncSession = Depends(get_db),
):
    # Валидация типа файла
    if not file.content_type or not file.content_type.startswith('video/'):
        raise HTTPException(
            status_code=400, 
            detail="Только видео файлы поддерживаются (video/*)"
        )
    
    ac = await db.get(ARContent, content_id)
    if not ac:
        raise HTTPException(status_code=404, detail="AR content not found")

    videos_dir = Path(settings.STORAGE_BASE_PATH) / "ar_content" / str(ac.unique_id) / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)

    video_path = videos_dir / file.filename
    async with aiofiles.open(video_path, "wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            await out.write(chunk)

    v = Video(
        ar_content_id=ac.id,
        video_path=str(video_path),
        video_url=_build_public_url(video_path),
        title=title or file.filename,
        is_active=is_active,
        mime_type=file.content_type,
    )
    db.add(v)
    await db.flush()
    if is_active:
        ac.active_video_id = v.id
    await db.commit()
    await db.refresh(v)

    # Запускаем фоновую генерацию превью
    thumbnail_task = generate_video_thumbnail.delay(v.id)

    return {
        "id": v.id,
        "video_url": v.video_url,
        "is_active": v.is_active,
        "thumbnail_task_id": thumbnail_task.id,
    }


@router.post("/ar-content/{content_id}/generate-marker")
async def trigger_marker_generation(content_id: int, db: AsyncSession = Depends(get_db)):
    ac = await db.get(ARContent, content_id)
    if not ac:
        raise HTTPException(status_code=404, detail="AR content not found")
    if ac.marker_status == "processing":
        return {"status": "already_processing"}
    ac.marker_status = "processing"
    await db.commit()
    task = generate_ar_content_marker_task.delay(content_id)
    return {"task_id": task.id, "status": "processing_started"}
    stmt = select(ARContent).where(ARContent.unique_id == unique_id)
    res = await db.execute(stmt)
    ac = res.scalar_one_or_none()
    if not ac:
        raise HTTPException(status_code=404, detail="AR content not found")
    if not ac.active_video_id:
        raise HTTPException(status_code=404, detail="No active video")
    vid = await db.get(Video, ac.active_video_id)
    if not vid:
        raise HTTPException(status_code=404, detail="Active video missing")
    return {"video_url": vid.video_url}


@router.get("/ar/{unique_id}/active-video")
async def get_active_video(unique_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(ARContent).where(ARContent.unique_id == unique_id)
    res = await db.execute(stmt)
    ac = res.scalar_one_or_none()
    if not ac:
        raise HTTPException(status_code=404, detail="AR content not found")
    if not ac.active_video_id:
        raise HTTPException(status_code=404, detail="No active video")
    vid = await db.get(Video, ac.active_video_id)
    if not vid:
        raise HTTPException(status_code=404, detail="Active video missing")
    return {"video_url": vid.video_url}
    stmt = select(ARContent).where(ARContent.unique_id == unique_id)
    res = await db.execute(stmt)
    ac = res.scalar_one_or_none()
    if not ac:
        raise HTTPException(status_code=404, detail="AR content not found")
    return {
        "id": ac.id,
        "unique_id": str(ac.unique_id),
        "marker_status": ac.marker_status,
        "marker_url": ac.marker_url,
        "image_url": ac.image_url,
    }
