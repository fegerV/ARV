from pathlib import Path
from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone, timedelta

from app.core.config import settings
from app.core.database import get_db
from app.models.ar_content import ARContent
from app.schemas.viewer import VIEWER_MANIFEST_VERSION, ViewerManifestResponse, ViewerManifestVideo
from app.services.video_scheduler import get_active_video, update_rotation_state
from app.utils.ar_content import build_public_url

logger = structlog.get_logger()
router = APIRouter()


def _absolute_url(relative_path: str) -> str:
    """Build absolute URL from relative path (e.g. /storage/...)."""
    base = settings.PUBLIC_URL.rstrip("/")
    path = (relative_path or "").strip()
    if not path:
        return base
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return f"{base}{path}" if path.startswith("/") else f"{base}/{path}"


def _photo_url_from_ar_content(ar_content: ARContent) -> Optional[str]:
    """Get photo URL (relative) from ARContent, recalculating from path if needed."""
    url = ar_content.photo_url
    if ar_content.photo_path:
        try:
            p = Path(ar_content.photo_path)
            path_abs = p if p.is_absolute() else Path(settings.STORAGE_BASE_PATH) / ar_content.photo_path
            url = build_public_url(path_abs)
        except Exception:
            pass
    return url


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
        "thumbnail_url": video.preview_url,
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
        "thumbnail_url": video.preview_url,
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


@router.get("/ar/{unique_id}/check")
async def get_viewer_content_check(
    unique_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Check if AR content is available for viewing without incrementing view count.
    Returns content_available and optional reason. Use before showing UI or fetching full manifest.
    """
    try:
        UUID(unique_id)
    except (ValueError, TypeError):
        logger.info("viewer_check_invalid_id", unique_id=unique_id)
        return {"content_available": False, "reason": "invalid_unique_id"}

    stmt = select(ARContent).where(ARContent.unique_id == unique_id)
    res = await db.execute(stmt)
    ar_content = res.scalar_one_or_none()
    if not ar_content:
        logger.info("viewer_check_not_found", unique_id=unique_id)
        return {"content_available": False, "reason": "not_found"}

    creation = ar_content.created_at.replace(tzinfo=None) if ar_content.created_at.tzinfo else ar_content.created_at
    expiry_date = creation + timedelta(days=ar_content.duration_years * 365)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if now > expiry_date:
        logger.info("viewer_check_expired", unique_id=unique_id)
        return {"content_available": False, "reason": "subscription_expired"}

    if ar_content.status not in ["active", "ready"]:
        logger.info("viewer_check_not_active", unique_id=unique_id, status=ar_content.status)
        return {"content_available": False, "reason": "content_not_active"}

    if not (ar_content.photo_url or ar_content.photo_path):
        logger.info("viewer_check_no_photo", unique_id=unique_id)
        return {"content_available": False, "reason": "marker_image_not_available"}

    if (ar_content.marker_status or "").strip().lower() != "ready":
        logger.info(
            "viewer_check_marker_not_ready",
            unique_id=unique_id,
            marker_status=ar_content.marker_status,
        )
        return {"content_available": False, "reason": "marker_still_generating"}

    video_result = await get_active_video(ar_content.id, db)
    if not video_result:
        logger.info("viewer_check_no_video", unique_id=unique_id, ar_content_id=ar_content.id)
        return {"content_available": False, "reason": "no_playable_video"}

    logger.info("viewer_check_ok", unique_id=unique_id, ar_content_id=ar_content.id)
    return {"content_available": True}


@router.get("/ar/{unique_id}/manifest", response_model=ViewerManifestResponse)
async def get_viewer_manifest(
    unique_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get viewer manifest for Android ARCore app.
    Returns marker image URL (photo), video, expiry; increments views_count.
    """
    try:
        UUID(unique_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid unique_id format")

    stmt = select(ARContent).where(ARContent.unique_id == unique_id)
    res = await db.execute(stmt)
    ar_content = res.scalar_one_or_none()
    if not ar_content:
        raise HTTPException(status_code=404, detail="AR content not found")

    creation = ar_content.created_at.replace(tzinfo=None) if ar_content.created_at.tzinfo else ar_content.created_at
    expiry_date = creation + timedelta(days=ar_content.duration_years * 365)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if now > expiry_date:
        raise HTTPException(status_code=403, detail="AR content subscription has expired")

    if ar_content.status not in ["active", "ready"]:
        raise HTTPException(status_code=400, detail="AR content is not active or ready")

    photo_url_rel = _photo_url_from_ar_content(ar_content)
    if not photo_url_rel:
        raise HTTPException(status_code=400, detail="Photo (marker image) not available")

    if (ar_content.marker_status or "").strip().lower() != "ready":
        raise HTTPException(
            status_code=400,
            detail="Marker is still being generated, try again later",
        )

    video_result = await get_active_video(ar_content.id, db)
    if not video_result:
        raise HTTPException(status_code=400, detail="No playable videos available for this AR content")

    video = video_result["video"]
    source = video_result["source"]
    schedule_id = video_result.get("schedule_id")
    expires_in = video_result.get("expires_in")
    if source == "rotation" and getattr(video, "rotation_type", None) in ["sequential", "cyclic"]:
        await update_rotation_state(ar_content, db)

    marker_image_url = _absolute_url(photo_url_rel)
    photo_url_abs = _absolute_url(photo_url_rel)
    video_url_abs = _absolute_url(video.video_url or "")
    thumbnail_url_abs = _absolute_url(video.preview_url) if video.preview_url else None

    try:
        ar_content.views_count = (ar_content.views_count or 0) + 1
        await db.commit()
        await db.refresh(ar_content)
        logger.info("viewer_manifest_views_incremented", ar_content_id=ar_content.id, views_count=ar_content.views_count)
    except Exception as e:
        logger.warning("failed_to_increment_views_manifest", error=str(e))
        await db.rollback()

    expires_at_str = expiry_date.isoformat() if hasattr(expiry_date, "isoformat") else str(expiry_date)
    video_payload = ViewerManifestVideo(
        id=video.id,
        title=video.filename,
        video_url=video_url_abs,
        thumbnail_url=thumbnail_url_abs,
        duration=video.duration,
        width=video.width,
        height=video.height,
        mime_type=video.mime_type,
        selection_source=source,
        schedule_id=schedule_id,
        expires_in_days=expires_in,
        selected_at=datetime.now(timezone.utc).isoformat(),
    )
    response = ViewerManifestResponse(
        manifest_version=VIEWER_MANIFEST_VERSION,
        unique_id=unique_id,
        order_number=ar_content.order_number or "",
        marker_image_url=marker_image_url,
        photo_url=photo_url_abs,
        video=video_payload,
        expires_at=expires_at_str,
        status=ar_content.status or "ready",
    )
    logger.info(
        "viewer_manifest_served",
        unique_id=unique_id,
        ar_content_id=ar_content.id,
        marker_image_url=marker_image_url,
        video_url=video_url_abs,
    )
    return JSONResponse(
        content=response.model_dump(mode="json"),
        headers={"X-Manifest-Version": VIEWER_MANIFEST_VERSION},
    )