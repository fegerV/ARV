from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.ar_content import ARContent
from app.models.video import Video
from app.services.video_scheduler import get_active_video

router = APIRouter(prefix="/public", tags=["Public"])
@router.get("/ar/{unique_id}/active-video")
async def get_active_video_endpoint(unique_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(ARContent).where(ARContent.unique_id == unique_id)
    res = await db.execute(stmt)
    ac = res.scalar_one_or_none()
    if not ac or not ac.is_active:
        raise HTTPException(status_code=404, detail="AR content not found or inactive")

    vid = await get_active_video(ac.id, db)
    if not vid:
        raise HTTPException(status_code=404, detail="No active video available")

    return {
        "id": vid.id,
        "title": vid.title,
        "video_url": vid.video_url,
        "thumbnail_url": vid.thumbnail_url,
        "duration": vid.duration,
    }


@router.get("/ar/{unique_id}/content")
async def get_public_ar_content(unique_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(ARContent).where(ARContent.unique_id == unique_id)
    res = await db.execute(stmt)
    ac = res.scalar_one_or_none()
    if not ac:
        raise HTTPException(status_code=404, detail="AR content not found")
    active_video_url = None
    if ac.active_video_id:
        vid = await db.get(Video, ac.active_video_id)
        if vid:
            active_video_url = vid.video_url
    return {
        "id": ac.id,
        "unique_id": str(ac.unique_id),
        "title": ac.title,
        "image_url": ac.image_url,
        "marker_url": ac.marker_url,
        "marker_status": ac.marker_status,
        "active_video_url": active_video_url,
    }
