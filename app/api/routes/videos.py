from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.video import Video
from app.models.ar_content import ARContent

router = APIRouter()


@router.get("/ar-content/{content_id}/videos")
async def list_videos(content_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Video).where(Video.ar_content_id == content_id)
    res = await db.execute(stmt)
    vids = res.scalars().all()
    return [
        {
            "id": v.id,
            "title": v.title,
            "video_url": v.video_url,
            "is_active": v.is_active,
            "rotation_order": v.rotation_order,
        }
        for v in vids
    ]


@router.put("/videos/{video_id}")
async def update_video(video_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    v = await db.get(Video, video_id)
    if not v:
        raise HTTPException(status_code=404, detail="Video not found")
    for k, val in payload.items():
        if hasattr(v, k):
            setattr(v, k, val)
    await db.commit()
    return {"status": "updated"}


@router.delete("/videos/{video_id}")
async def delete_video(video_id: int, db: AsyncSession = Depends(get_db)):
    v = await db.get(Video, video_id)
    if not v:
        raise HTTPException(status_code=404, detail="Video not found")
    await db.delete(v)
    await db.commit()
    return {"status": "deleted"}


@router.post("/videos/{video_id}/activate")
async def activate_video(video_id: int, db: AsyncSession = Depends(get_db)):
    v = await db.get(Video, video_id)
    if not v:
        raise HTTPException(status_code=404, detail="Video not found")
    ac = await db.get(ARContent, v.ar_content_id)
    if not ac:
        raise HTTPException(status_code=404, detail="AR content not found")
    ac.active_video_id = v.id
    v.is_active = True
    await db.commit()
    return {"status": "activated", "active_video_id": ac.active_video_id}


@router.put("/videos/{video_id}/schedule")
async def update_video_schedule(video_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    v = await db.get(Video, video_id)
    if not v:
        raise HTTPException(status_code=404, detail="Video not found")
    # Accept ISO8601 strings or nulls for schedule window
    v.schedule_start = payload.get("schedule_start")
    v.schedule_end = payload.get("schedule_end")
    await db.commit()
    return {"status": "updated"}
