from uuid import uuid4
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import aiofiles
import structlog

from app.core.config import settings
from app.core.database import get_db
from app.models.ar_content import ARContent
from app.models.video import Video
from app.models.ar_view_session import ARViewSession
from app.models.project import Project
from app.models.company import Company
from app.tasks.marker_tasks import generate_ar_content_marker_task
from app.tasks.preview_tasks import generate_video_thumbnail, generate_image_thumbnail

logger = structlog.get_logger()

router = APIRouter(prefix="/ar-content", tags=["AR Content"])


def _build_public_url(saved: Path) -> str:
    base = Path(settings.STORAGE_BASE_PATH)
    rel = saved.relative_to(base)
    return f"/storage/{rel.as_posix()}"


@router.post("/")
async def create_ar_content(
    company_id: int = Form(...),
    project_id: int = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    client_name: Optional[str] = Form(None),
    client_phone: Optional[str] = Form(None),
    client_email: Optional[str] = Form(None),
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
        client_name=client_name,
        client_phone=client_phone,
        client_email=client_email,
        image_path=str(image_path),
        image_url=_build_public_url(image_path),
        marker_status="pending",
        is_active=True,
        content_metadata={},
    )
    db.add(ac)
    await db.flush()
    await db.commit()
    await db.refresh(ac)

    # Запускаем задачу генерации маркера
    task = generate_ar_content_marker_task.delay(ac.id)
    
    # Запускаем задачу генерации превью для изображения
    try:
        generate_image_thumbnail.delay(ac.id)
    except Exception as e:
        # Логируем ошибку, но не прерываем основной процесс
        logger.error("failed_to_start_image_thumbnail_generation", ar_content_id=ac.id, error=str(e))

    return {
        "id": ac.id,
        "unique_id": str(ac.unique_id),
        "image_url": ac.image_url,
        "thumbnail_url": ac.thumbnail_url,
        "marker_status": ac.marker_status,
        "task_id": task.id,
    }


@router.get("/")
async def list_all_ar_content(db: AsyncSession = Depends(get_db)):
    """List all AR content across all projects and companies"""
    from app.models.project import Project
    from app.models.company import Company
    
    stmt = select(ARContent, Project, Company).join(Project, ARContent.project_id == Project.id).join(Company, Project.company_id == Company.id)
    res = await db.execute(stmt)
    
    items = []
    for ac, proj, company in res.all():
        # Get active video info
        active_video_title = None
        if ac.active_video_id:
            video_stmt = select(Video).where(Video.id == ac.active_video_id)
            video_res = await db.execute(video_stmt)
            video = video_res.scalar_one_or_none()
            if video:
                active_video_title = video.title
        
        # Get view count
        views_stmt = select(func.count()).select_from(ARViewSession).where(ARViewSession.ar_content_id == ac.id)
        views_res = await db.execute(views_stmt)
        view_count = views_res.scalar() or 0
        
        items.append({
            "id": ac.id,
            "unique_id": str(ac.unique_id),
            "order_number": f"{ac.id:06d}",
            "title": ac.title,
            "marker_status": ac.marker_status,
            "image_url": ac.image_url,
            "thumbnail_url": ac.thumbnail_url,
            "created_at": ac.created_at.isoformat() if ac.created_at else None,
            "is_active": ac.is_active,
            "client_name": ac.client_name or "",
            "client_phone": ac.client_phone or "",
            "client_email": ac.client_email or "",
            "views": view_count,
            "project": {
                "id": proj.id,
                "name": proj.name
            },
            "company": {
                "id": company.id,
                "name": company.name
            },
            "active_video": {
                "id": ac.active_video_id,
                "title": active_video_title
            }
        })
    
    return {"items": items}


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
            "thumbnail_url": ac.thumbnail_url,
        })
    return {"items": items}


@router.post("/{content_id}/videos")
async def upload_video(
    content_id: int,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    is_active: bool = Form(False),
    db: AsyncSession = Depends(get_db),
):
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
        title=title,
        is_active=is_active,
    )
    db.add(v)
    await db.flush()
    if is_active:
        ac.active_video_id = v.id
    await db.commit()
    await db.refresh(v)
    await db.refresh(ac)

    # Запускаем задачу генерации превью
    try:
        generate_video_thumbnail.delay(v.id)
    except Exception as e:
        # Логируем ошибку, но не прерываем основной процесс
        logger.error("failed_to_start_video_thumbnail_generation", video_id=v.id, error=str(e))

    return {
        "id": v.id,
        "video_url": v.video_url,
        "thumbnail_url": v.thumbnail_url,
        "is_active": v.is_active,
    }


@router.post("/{content_id}/generate-marker")
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


@router.get("/ar/{unique_id}")
async def get_ar_content(unique_id: str, db: AsyncSession = Depends(get_db)):
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
        "thumbnail_url": ac.thumbnail_url,
    }


@router.get("/{content_id}")
async def get_ar_content_detail(content_id: int, db: AsyncSession = Depends(get_db)):
    # Get AR content
    ac = await db.get(ARContent, content_id)
    if not ac:
        raise HTTPException(status_code=404, detail="AR content not found")
    
    # Get project and company info
    from app.models.project import Project
    from app.models.company import Company
    proj = await db.get(Project, ac.project_id)
    company = await db.get(Company, proj.company_id) if proj else None
    
    # Get videos
    from app.models.video import Video
    videos_stmt = select(Video).where(Video.ar_content_id == content_id)
    videos_res = await db.execute(videos_stmt)
    videos = videos_res.scalars().all()
    
    # Get stats (mock data for now)
    from app.models.ar_view_session import ARViewSession
    from sqlalchemy import func
    views_stmt = select(func.count()).select_from(ARViewSession).where(ARViewSession.ar_content_id == content_id)
    views_res = await db.execute(views_stmt)
    view_count = views_res.scalar() or 0
    
    # Format response
    ar_content_data = {
        "id": ac.id,
        "title": ac.title,
        "uniqueId": str(ac.unique_id),
        "imageUrl": ac.image_url,
        "thumbnailUrl": ac.thumbnail_url,
        "imageWidth": 1920,  # Mock data
        "imageHeight": 1080,  # Mock data
        "imageSize": 2048000,  # Mock data (2MB)
        "mimeType": "image/jpeg",
        "markerStatus": ac.marker_status,
        "markerFileName": f"{ac.unique_id}.mind" if ac.marker_url else None,
        "markerSize": 102400 if ac.marker_url else None,  # Mock data (100KB)
        "markerFeaturePoints": 800,  # Mock data
        "markerGenerationTime": 5.2,  # Mock data
        "createdAt": ac.created_at.isoformat() if ac.created_at else None,
        "createdBy": "Admin User",  # Mock data
    }
    
    videos_data = [
        {
            "id": v.id,
            "fileName": f"video_{v.id}.mp4",
            "fileSize": v.size_bytes or 10485760,  # Mock data (10MB)
            "duration": v.duration or 30.0,  # Mock data
            "width": v.width or 1920,  # Mock data
            "height": v.height or 1080,  # Mock data
            "fps": 30,  # Mock data
            "codec": "H.264",
            "previewUrl": v.thumbnail_url or "/static/placeholder-video.png",
            "videoUrl": v.video_url,
            "isActive": v.is_active,
            "scheduleType": "default",
        }
        for v in videos
    ]
    
    stats_data = {
        "totalViews": view_count,
        "uniqueSessions": max(0, view_count - 5),  # Mock data
        "avgSessionDuration": 45.5,  # Mock data
        "avgFps": 58.3,  # Mock data
        "deviceBreakdown": [
            {"device": "iPhone 12", "percentage": 45},
            {"device": "Samsung Galaxy S21", "percentage": 30},
            {"device": "iPad Pro", "percentage": 15},
            {"device": "Other", "percentage": 10},
        ]
    }
    
    company_data = {
        "name": company.name if company else "Unknown Company"
    }
    
    project_data = {
        "name": proj.name if proj else "Unknown Project"
    }
    
    return {
        "arContent": ar_content_data,
        "videos": videos_data,
        "stats": stats_data,
        "company": company_data,
        "project": project_data,
    }