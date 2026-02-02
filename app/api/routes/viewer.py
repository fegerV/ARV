from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.core.database import get_db
from app.models.ar_content import ARContent
from app.services.video_scheduler import get_active_video, update_rotation_state

router = APIRouter()


@router.get("/viewer/{ar_content_id}/active-video")
async def get_viewer_active_video(
    ar_content_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get the active video for AR content viewer with metadata.
    
    This endpoint implements the video selection logic with priority:
    1. Date-specific rules (holidays, special dates) - highest priority
    2. Video with active schedule window
    3. VideoRotationSchedule rule (fixed, daily_cycle, weekly_cycle, random_daily)
    4. ARContent.active_video_id (if not expired)
    5. Legacy rotation (sequential/cyclic)
    6. Any active video (fallback)
    
    Skips videos with expired subscriptions.
    """
    # Verify AR content exists and is active
    ar_content = await db.get(ARContent, ar_content_id)
    if not ar_content:
        raise HTTPException(status_code=404, detail="AR content not found")
    
    # Check if AR content is active (status should be "active" or "ready")
    if ar_content.status not in ["active", "ready"]:
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
    
    # Update rotation state if video was selected via legacy rotation (sequential/cyclic)
    # New rotation types (daily_cycle, weekly_cycle, etc.) don't need state updates
    if source == "rotation" and hasattr(video, 'rotation_type') and video.rotation_type in ["sequential", "cyclic"]:
        await update_rotation_state(ar_content, db)
    
    # Build response with video metadata and selection info
    response = {
        "id": video.id,
        "title": video.filename,  # Use filename as title
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
        "selected_at": datetime.now(timezone.utc).isoformat(),
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

    if not ar_content or ar_content.status not in ["active", "ready"]:
        raise HTTPException(status_code=404, detail="AR content not found or not active")

    video_result = await get_active_video(ar_content.id, db)
    if not video_result:
        raise HTTPException(status_code=404, detail="No playable videos available for this AR content")

    video = video_result["video"]
    source = video_result["source"]
    schedule_id = video_result.get("schedule_id")
    expires_in = video_result.get("expires_in")
    
    # Update rotation state if video was selected via legacy rotation (sequential/cyclic)
    # New rotation types (daily_cycle, weekly_cycle, date_rule, etc.) don't need state updates
    if source == "rotation" and hasattr(video, 'rotation_type') and video.rotation_type in ["sequential", "cyclic"]:
        await update_rotation_state(ar_content, db)

    return {
        "id": video.id,
        "title": video.filename,  # Use filename as title
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
        "selected_at": datetime.now(timezone.utc).isoformat(),
        "video_created_at": video.created_at.isoformat() if video.created_at else None,
    }