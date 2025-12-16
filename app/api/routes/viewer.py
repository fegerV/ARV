from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.core.database import get_db
from app.models.ar_content import ARContent
from app.services.video_scheduler import get_active_video

router = APIRouter()


@router.get("/viewer/{ar_content_id}/active-video")
async def get_viewer_active_video(
    ar_content_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get the active video for AR content viewer with metadata.
    
    This endpoint implements the video selection logic:
    1. Prefer video with active schedule window
    2. Honor rotation_type (none -> active video, sequential -> advance, cyclic -> wrap)
    3. Skip videos with expired subscriptions
    4. Return metadata about selection source and expiration
    """
    # Verify AR content exists and is active
    ar_content = await db.get(ARContent, ar_content_id)
    if not ar_content:
        raise HTTPException(status_code=404, detail="AR content not found")
    
    if not ar_content.is_active:
        raise HTTPException(status_code=404, detail="AR content is not active")
    
    # Get the active video using the scheduler service
    video_result = await get_active_video(ar_content_id, db)
    
    if not video_result:
        raise HTTPException(
            status_code=404, 
            detail="No playable videos available for this AR content"
        )
    
    video = video_result["video"]
    source = video_result["source"]
    schedule_id = video_result.get("schedule_id")
    expires_in = video_result.get("expires_in")
    
    # Build response with video metadata and selection info
    response = {
        "id": video.id,
        "title": video.title,
        "video_url": video.video_url,
        "preview_url": video.preview_url,
        "thumbnail_url": video.thumbnail_url,
        "duration": video.duration,
        "width": video.width,
        "height": video.height,
        "mime_type": video.mime_type,
        
        # Selection metadata
        "selection_source": source,  # 'schedule', 'active_default', 'rotation', 'fallback'
        "schedule_id": schedule_id,
        "expires_in_days": expires_in,
        
        # Video state info
        "is_active": video.is_active,
        "rotation_type": video.rotation_type,
        "subscription_end": video.subscription_end,
        
        # Timestamps
        "selected_at": datetime.utcnow().isoformat(),
        "video_created_at": video.created_at.isoformat() if video.created_at else None,
    }
    
    return response


@router.get("/ar/{unique_id}/active-video")
async def get_viewer_active_video_by_unique_id(
    unique_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get the active video for AR viewer by ARContent.unique_id."""
    stmt = select(ARContent).where(ARContent.unique_id == unique_id)
    res = await db.execute(stmt)
    ar_content = res.scalar_one_or_none()

    if not ar_content or not ar_content.is_active:
        raise HTTPException(status_code=404, detail="AR content not found")

    video_result = await get_active_video(ar_content.id, db)
    if not video_result:
        raise HTTPException(status_code=404, detail="No playable videos available for this AR content")

    video = video_result["video"]
    source = video_result["source"]
    schedule_id = video_result.get("schedule_id")
    expires_in = video_result.get("expires_in")

    return {
        "id": video.id,
        "title": video.title,
        "video_url": video.video_url,
        "preview_url": video.preview_url,
        "thumbnail_url": video.thumbnail_url,
        "duration": video.duration,
        "width": video.width,
        "height": video.height,
        "mime_type": video.mime_type,
        "selection_source": source,
        "schedule_id": schedule_id,
        "expires_in_days": expires_in,
        "is_active": video.is_active,
        "rotation_type": video.rotation_type,
        "subscription_end": video.subscription_end,
        "selected_at": datetime.utcnow().isoformat(),
        "video_created_at": video.created_at.isoformat() if video.created_at else None,
    }