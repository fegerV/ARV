from uuid import uuid4
from pathlib import Path
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
import aiofiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.database import get_db
from app.core.errors import AppException
from app.models.ar_content import ARContent
from app.models.video import Video
from app.models.company import Company
from app.models.project import Project
from app.models.video_rotation_schedule import VideoRotationSchedule
from app.models.ar_view_session import ARViewSession
from app.schemas.ar_content import ARContentDetailResponse, ARContentStats, RotationRuleShort
from app.schemas.ar_content_list import ARContentListItem
from app.schemas.ar_content_filter import ARContentFilter
from app.schemas.pagination import PaginatedResponse
from app.tasks.marker_tasks import generate_ar_content_marker_task
from app.tasks.thumbnail_generator import generate_video_thumbnail, generate_image_thumbnail
from fastapi import Query

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/api/ar-content", tags=["ar-content"])


def _build_public_url(saved: Path) -> str:
    base = Path(settings.STORAGE_BASE_PATH)
    rel = saved.relative_to(base)
    return f"/storage/{rel.as_posix()}"


def _serialize_rotation_rule(rule: VideoRotationSchedule | None) -> RotationRuleShort | None:
    if not rule:
        return None

    human_map = {
        "fixed": "Одно видео",
        "daily_cycle": "Ежедневная ротация",
        "date_specific": "По конкретным датам",
        "random_daily": "Случайное видео каждый день",
    }

    return RotationRuleShort(
        type=rule.rotation_type,
        type_human=human_map.get(rule.rotation_type, rule.rotation_type),
        default_video_title=None,  # TODO: получить заголовок видео по умолчанию
        next_change_at=rule.next_rotation_at,
        next_change_at_readable=(
            rule.next_rotation_at.astimezone().strftime("%d.%m.%Y %H:%M")
            if rule.next_rotation_at else None
        ),
    )


async def _get_ar_content_stats(
    db: AsyncSession,
    ar_content_id: int,
    days: int = 30,
) -> ARContentStats:
    since = func.now() - func.make_interval(0, 0, 0, days)  # last N days

    # общее количество просмотров и уникальные сессии
    base_stmt = (
        select(
            func.count(ARViewSession.id).label("views"),
            func.count(func.distinct(ARViewSession.session_id)).label("unique_sessions"),
            func.coalesce(func.avg(ARViewSession.duration_seconds), 0).label("avg_duration"),
            func.coalesce(func.avg(ARViewSession.avg_fps), 0).label("avg_fps"),
        )
        .where(ARViewSession.ar_content_id == ar_content_id)
        .where(ARViewSession.created_at >= since)
    )

    result = await db.execute(base_stmt)
    row = result.one()

    return ARContentStats(
        views=row.views or 0,
        unique_sessions=row.unique_sessions or 0,
        avg_duration=float(row.avg_duration or 0),
        avg_fps=float(row.avg_fps or 0),
    )


@router.get("/{ar_content_id}", response_model=ARContentDetailResponse)
@limiter.limit("30/minute")  # Rate limit: 30 requests per minute
async def get_ar_content_detail(
    request: Request,
    ar_content_id: int,
    db: AsyncSession = Depends(get_db)
):
    # 1. Основные данные + связи
    stmt = (
        select(ARContent)
        .options(
            selectinload(ARContent.company),
            selectinload(ARContent.project),
            selectinload(ARContent.videos),
            selectinload(ARContent.rotation_rule),
        )
        .where(ARContent.id == ar_content_id)
    )
    result = await db.execute(stmt)
    ar_content: ARContent | None = result.scalar_one_or_none()

    if not ar_content:
        raise AppException(
            status_code=404,
            detail="AR-контент не найден",
            code="AR_CONTENT_NOT_FOUND",
        )

    # 2. Статистика за последние 30 дней
    stats = await _get_ar_content_stats(db, ar_content.id)

    # 3. Сбор DTO
    return ARContentDetailResponse(
        id=ar_content.id,
        unique_id=str(ar_content.unique_id),
        title=ar_content.title,
        description=ar_content.description,
        company_id=ar_content.company_id,
        company_name=ar_content.company.name if ar_content.company else None,
        project_id=ar_content.project_id,
        project_name=ar_content.project.name if ar_content.project else None,
        image_url=ar_content.image_url,
        thumbnail_url=ar_content.thumbnail_url,
        image_width=ar_content.content_metadata.get("width") if ar_content.content_metadata else None,
        image_height=ar_content.content_metadata.get("height") if ar_content.content_metadata else None,
        image_size_readable=ar_content.content_metadata.get("size_readable") if ar_content.content_metadata else None,
        image_path=ar_content.image_path,
        marker_status=ar_content.marker_status,
        marker_url=ar_content.marker_url,
        marker_path=ar_content.marker_path,
        marker_feature_points=(
            ar_content.marker_metadata.get("feature_points")
            if ar_content.marker_metadata else None
        ),
        videos=[
            {
                "id": v.id,
                "title": v.title,
                "video_url": v.video_url,
                "thumbnail_url": v.thumbnail_url,
                "duration": v.duration,
            }
            for v in ar_content.videos
        ],
        rotation_rule=_serialize_rotation_rule(ar_content.rotation_rule),
        stats=stats,
        created_at=ar_content.created_at,
        expires_at=ar_content.expires_at,
    )


@router.get("/", response_model=PaginatedResponse[ARContentListItem])
@limiter.limit("60/minute")  # Rate limit: 60 requests per minute
async def list_ar_content(
    request: Request,
    filters: ARContentFilter = Depends(),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, le=100),
    db: AsyncSession = Depends(get_db)
):
    # Base query
    stmt = select(ARContent).options(
        selectinload(ARContent.company),
        selectinload(ARContent.project),
    )
    
    # Apply filters
    if filters.search:
        stmt = stmt.where(
            (ARContent.title.icontains(filters.search)) |
            (ARContent.description.icontains(filters.search))
        )
    
    if filters.company_id:
        stmt = stmt.where(ARContent.company_id == filters.company_id)
        
    if filters.project_id:
        stmt = stmt.where(ARContent.project_id == filters.project_id)
        
    if filters.marker_status:
        stmt = stmt.where(ARContent.marker_status == filters.marker_status)
        
    if filters.is_active is not None:
        stmt = stmt.where(ARContent.is_active == filters.is_active)
        
    if filters.date_from:
        stmt = stmt.where(ARContent.created_at >= filters.date_from)
        
    if filters.date_to:
        stmt = stmt.where(ARContent.created_at <= filters.date_to)
    
    # Count total items
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()
    
    # Apply pagination
    offset = (page - 1) * per_page
    stmt = stmt.offset(offset).limit(per_page)
    
    # Execute query
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    # Transform to list items
    list_items = []
    for item in items:
        # Count videos for this item
        video_count_stmt = select(func.count(Video.id)).where(Video.ar_content_id == item.id)
        video_count_result = await db.execute(video_count_stmt)
        video_count = video_count_result.scalar_one()
        
        # Count views for this item
        views_count_stmt = select(func.count(ARViewSession.id)).where(ARViewSession.ar_content_id == item.id)
        views_count_result = await db.execute(views_count_stmt)
        views_count = views_count_result.scalar_one()
        
        list_items.append(ARContentListItem(
            id=item.id,
            unique_id=str(item.unique_id),
            title=item.title,
            description=item.description,
            company_id=item.company_id,
            company_name=item.company.name if item.company else None,
            project_id=item.project_id,
            project_name=item.project.name if item.project else None,
            image_url=item.image_url,
            thumbnail_url=item.thumbnail_url,
            videos_count=video_count,
            marker_status=item.marker_status,
            views_count=views_count,
            created_at=item.created_at,
            expires_at=item.expires_at,
        ))
    
    # Calculate total pages
    total_pages = (total + per_page - 1) // per_page
    
    return PaginatedResponse(
        items=list_items,
        meta={
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
        }
    )


@router.post("/ar-content")
@limiter.limit("10/minute")  # Rate limit: 10 requests per minute for heavy operations
async def create_ar_content(
    request: Request,
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


@router.post("/ar-content/{content_id}/videos")
@limiter.limit("10/minute")  # Rate limit: 10 requests per minute for heavy operations
async def upload_video(
    request: Request,
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
        raise AppException(
            status_code=404,
            detail="AR-контент не найден",
            code="AR_CONTENT_NOT_FOUND",
        )

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
@limiter.limit("5/minute")  # Rate limit: 5 requests per minute for heavy operations
async def trigger_marker_generation(
    request: Request,
    content_id: int, 
    db: AsyncSession = Depends(get_db)
):
    ac = await db.get(ARContent, content_id)
    if not ac:
        raise AppException(
            status_code=404,
            detail="AR-контент не найден",
            code="AR_CONTENT_NOT_FOUND",
        )
    if ac.marker_status == "processing":
        return {"status": "already_processing"}
    ac.marker_status = "processing"
    await db.commit()
    task = generate_ar_content_marker_task.delay(content_id)
    return {"task_id": task.id, "status": "processing_started"}


@router.get("/ar/{unique_id}/active-video")
@limiter.limit("100/minute")  # Higher rate limit for public endpoints
async def get_active_video(request: Request, unique_id: str, db: AsyncSession = Depends(get_db)):
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
@limiter.limit("100/minute")  # Higher rate limit for public endpoints
async def get_ar_content_public(request: Request, unique_id: str, db: AsyncSession = Depends(get_db)):
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


@router.put("/{ar_content_id}")
@limiter.limit("30/minute")  # Rate limit: 30 requests per minute
async def update_ar_content(
    request: Request,
    ar_content_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db)
):
    """Update AR content details."""
    ar_content = await db.get(ARContent, ar_content_id)
    if not ar_content:
        raise AppException(
            status_code=404,
            detail="AR-контент не найден",
            code="AR_CONTENT_NOT_FOUND",
        )
    
    # Update allowed fields
    allowed_fields = {
        "title", "description", "is_active", "expires_at"
    }
    
    for key, value in payload.items():
        if key in allowed_fields and hasattr(ar_content, key):
            setattr(ar_content, key, value)
    
    ar_content.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(ar_content)
    
    return {
        "id": ar_content.id,
        "title": ar_content.title,
        "updated_at": ar_content.updated_at.isoformat() if ar_content.updated_at else None
    }


@router.delete("/{ar_content_id}")
@limiter.limit("10/minute")  # Rate limit: 10 requests per minute
async def delete_ar_content(
    request: Request,
    ar_content_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete AR content and all associated videos."""
    ar_content = await db.get(ARContent, ar_content_id)
    if not ar_content:
        raise AppException(
            status_code=404,
            detail="AR-контент не найден",
            code="AR_CONTENT_NOT_FOUND",
        )
    
    # Store company ID for cleanup task
    company_id = ar_content.company_id
    
    # Trigger cleanup task for storage files
    from app.tasks.cleanup_tasks import cleanup_ar_content_storage
    cleanup_task = cleanup_ar_content_storage.delay(ar_content_id, company_id)
    
    await db.delete(ar_content)
    await db.commit()
    
    return {"status": "deleted", "id": ar_content_id, "cleanup_task_id": cleanup_task.id}
