from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.core.database import get_db
from app.core.errors import AppException
from app.models.video import Video
from app.models.ar_content import ARContent

router = APIRouter()


@router.get("/ar-content/{content_id}/videos")
async def list_videos(content_id: int, db: AsyncSession = Depends(get_db)):
    """List all videos for an AR content item."""
    stmt = select(Video).where(Video.ar_content_id == content_id)
    res = await db.execute(stmt)
    vids = res.scalars().all()
    return [
        {
            "id": v.id,
            "title": v.title,
            "video_url": v.video_url,
            "thumbnail_url": v.thumbnail_url,
            "is_active": v.is_active,
            "rotation_order": v.rotation_order,
            "duration": v.duration,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in vids
    ]


@router.get("/videos/{video_id}")
async def get_video(video_id: int, db: AsyncSession = Depends(get_db)):
    """Get video details by ID."""
    v = await db.get(Video, video_id)
    if not v:
        raise AppException(
            status_code=404,
            detail="Видео не найдено",
            code="VIDEO_NOT_FOUND",
        )
    return {
        "id": v.id,
        "title": v.title,
        "video_url": v.video_url,
        "thumbnail_url": v.thumbnail_url,
        "thumbnail_small_url": v.thumbnail_small_url,
        "thumbnail_large_url": v.thumbnail_large_url,
        "duration": v.duration,
        "width": v.width,
        "height": v.height,
        "is_active": v.is_active,
        "schedule_start": v.schedule_start.isoformat() if v.schedule_start else None,
        "schedule_end": v.schedule_end.isoformat() if v.schedule_end else None,
        "rotation_order": v.rotation_order,
        "created_at": v.created_at.isoformat() if v.created_at else None,
        "updated_at": v.updated_at.isoformat() if v.updated_at else None,
    }


@router.put("/videos/{video_id}")
async def update_video(video_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    """Update video details."""
    v = await db.get(Video, video_id)
    if not v:
        raise AppException(
            status_code=404,
            detail="Видео не найдено",
            code="VIDEO_NOT_FOUND",
        )
    
    # Update allowed fields
    allowed_fields = {
        "title", "is_active", "schedule_start", "schedule_end", "rotation_order"
    }
    
    for key, value in payload.items():
        if key in allowed_fields and hasattr(v, key):
            setattr(v, key, value)
    
    v.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(v)
    
    return {
        "id": v.id,
        "title": v.title,
        "is_active": v.is_active,
        "updated_at": v.updated_at.isoformat() if v.updated_at else None
    }


@router.delete("/videos/{video_id}")
async def delete_video(video_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a video."""
    v = await db.get(Video, video_id)
    if not v:
        raise AppException(
            status_code=404,
            detail="Видео не найдено",
            code="VIDEO_NOT_FOUND",
        )
    
    # Get company ID for cleanup task
    ar_content = await db.get(ARContent, v.ar_content_id)
    company_id = ar_content.company_id if ar_content else None
    
    # Trigger cleanup task for storage files
    from app.tasks.cleanup_tasks import cleanup_video_storage
    cleanup_task = cleanup_video_storage.delay(video_id, company_id)
    
    # Delete associated files from storage (optional cleanup)
    # This would require implementing storage cleanup logic
    
    await db.delete(v)
    await db.commit()
    
    return {"status": "deleted", "id": video_id, "cleanup_task_id": cleanup_task.id}


@router.post("/videos/{video_id}/activate")
async def activate_video(video_id: int, db: AsyncSession = Depends(get_db)):
    """Activate a video as the default for its AR content."""
    v = await db.get(Video, video_id)
    if not v:
        raise AppException(
            status_code=404,
            detail="Видео не найдено",
            code="VIDEO_NOT_FOUND",
        )
    ac = await db.get(ARContent, v.ar_content_id)
    if not ac:
        raise AppException(
            status_code=404,
            detail="AR-контент не найден",
            code="AR_CONTENT_NOT_FOUND",
        )
    ac.active_video_id = v.id
    v.is_active = True
    await db.commit()
    return {"status": "activated", "active_video_id": ac.active_video_id}


@router.put("/videos/{video_id}/schedule")
async def update_video_schedule(video_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    """Update video scheduling information."""
    v = await db.get(Video, video_id)
    if not v:
        raise AppException(
            status_code=404,
            detail="Видео не найдено",
            code="VIDEO_NOT_FOUND",
        )
    # Accept ISO8601 strings or nulls for schedule window
    v.schedule_start = payload.get("schedule_start")
    v.schedule_end = payload.get("schedule_end")
    v.updated_at = datetime.utcnow()
    await db.commit()
    return {"status": "updated"}