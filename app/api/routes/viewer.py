from pathlib import Path
from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone, timedelta

from app.core.config import settings
from app.core.database import get_db
from app.models.ar_content import ARContent
from app.models.ar_view_session import ARViewSession
from app.models.company import Company
from app.schemas.viewer import VIEWER_MANIFEST_VERSION, ViewerManifestResponse, ViewerManifestVideo
from app.services.video_scheduler import get_active_video, update_rotation_state
from app.utils.ar_content import build_public_url
from app.core.storage_providers import get_provider_for_company

logger = structlog.get_logger()
router = APIRouter()


def _is_yadisk_ref(path_or_url: Optional[str]) -> bool:
    """Check if a stored path is a ``yadisk://`` reference."""
    return bool(path_or_url and str(path_or_url).startswith("yadisk://"))


def _yadisk_relative(ref: str) -> str:
    """Extract relative path from ``yadisk://slug/project/001/file``."""
    return ref.replace("yadisk://", "", 1)


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
    """Get photo URL (relative or yadisk://) from ARContent."""
    url = ar_content.photo_url
    # For yadisk:// references, just return as-is (will be resolved later)
    if _is_yadisk_ref(url) or _is_yadisk_ref(ar_content.photo_path):
        return url
    if ar_content.photo_path:
        try:
            p = Path(ar_content.photo_path)
            path_abs = p if p.is_absolute() else Path(settings.STORAGE_BASE_PATH) / ar_content.photo_path
            url = build_public_url(path_abs)
        except Exception:
            pass
    return url


async def _resolve_yd_url(url_or_path: Optional[str], company: Company) -> Optional[str]:
    """Resolve a ``yadisk://`` reference to a temporary Yandex Disk download URL.

    Returns the original value unchanged if it is not a YD reference or if
    the company doesn't have a valid token.
    """
    if not url_or_path:
        return url_or_path
    if not _is_yadisk_ref(url_or_path):
        return url_or_path
    try:
        provider = await get_provider_for_company(company)
        from app.core.yandex_disk_provider import YandexDiskStorageProvider
        if isinstance(provider, YandexDiskStorageProvider):
            relative = _yadisk_relative(url_or_path)
            download_url = await provider.get_download_url(relative)
            if download_url:
                return download_url
    except Exception as exc:
        logger.error("yd_resolve_url_failed", path=url_or_path, error=str(exc))
    return url_or_path


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

    try:
        video_result = await get_active_video(ar_content.id, db)
    except Exception as exc:
        logger.error(
            "viewer_check_video_query_failed",
            unique_id=unique_id,
            ar_content_id=ar_content.id,
            error=str(exc),
            exc_info=True,
        )
        video_result = None

    if not video_result:
        logger.info("viewer_check_no_video", unique_id=unique_id, ar_content_id=ar_content.id)
        return {"content_available": False, "reason": "no_playable_video"}

    logger.info("viewer_check_ok", unique_id=unique_id, ar_content_id=ar_content.id)
    return {"content_available": True}


@router.get("/ar/{unique_id}/manifest", response_model=ViewerManifestResponse)
async def get_viewer_manifest(
    unique_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get viewer manifest for Android ARCore app.

    Returns marker image URL (photo), active video, expiry date;
    increments ``views_count`` and creates an ``ARViewSession`` for analytics.
    """
    try:
        UUID(unique_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid unique_id format")

    try:
        return await _build_manifest(unique_id, request, db)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "viewer_manifest_unhandled",
            unique_id=unique_id,
            error=str(exc),
            error_type=type(exc).__name__,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Manifest generation failed: {type(exc).__name__}: {exc}")


async def _build_manifest(
    unique_id: str,
    request: Request,
    db: AsyncSession,
) -> JSONResponse:
    """Core manifest builder extracted for clean error handling."""
    stmt = (
        select(ARContent)
        .options(selectinload(ARContent.company))
        .where(ARContent.unique_id == unique_id)
    )
    res = await db.execute(stmt)
    ar_content = res.scalar_one_or_none()
    if not ar_content:
        raise HTTPException(status_code=404, detail="AR content not found")

    # Save company reference early — before any commit that may expire relationships.
    company = ar_content.company

    creation = ar_content.created_at.replace(tzinfo=None) if ar_content.created_at.tzinfo else ar_content.created_at
    expiry_date = creation + timedelta(days=ar_content.duration_years * 365)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if now > expiry_date:
        raise HTTPException(status_code=403, detail="AR content subscription has expired")

    if ar_content.status not in ("active", "ready"):
        raise HTTPException(status_code=400, detail="AR content is not active or ready")

    photo_url_rel = _photo_url_from_ar_content(ar_content)
    if not photo_url_rel:
        raise HTTPException(status_code=400, detail="Photo (marker image) not available")

    if (ar_content.marker_status or "").strip().lower() != "ready":
        raise HTTPException(
            status_code=400,
            detail="Marker is still being generated, try again later",
        )

    # ── Active video selection ────────────────────────────────────────
    video_result = await get_active_video(ar_content.id, db)
    if not video_result:
        raise HTTPException(status_code=400, detail="No playable videos available for this AR content")

    video = video_result["video"]
    source = video_result["source"]
    schedule_id = video_result.get("schedule_id")
    expires_in = video_result.get("expires_in")

    if source == "rotation" and getattr(video, "rotation_type", None) in ("sequential", "cyclic"):
        await update_rotation_state(ar_content, db)

    # ── Resolve Yandex Disk yadisk:// references ─────────────────────
    if company and _is_yadisk_ref(photo_url_rel):
        photo_url_rel = await _resolve_yd_url(photo_url_rel, company)
    if company and _is_yadisk_ref(video.video_url):
        video.video_url = await _resolve_yd_url(video.video_url, company)
    if company and _is_yadisk_ref(video.preview_url):
        video.preview_url = await _resolve_yd_url(video.preview_url, company)

    # ── Build absolute URLs ──────────────────────────────────────────
    marker_image_url = _absolute_url(photo_url_rel)
    photo_url_abs = _absolute_url(photo_url_rel)
    video_url_abs = _absolute_url(video.video_url or "")
    thumbnail_url_abs = _absolute_url(video.preview_url) if video.preview_url else None

    # ── Increment views & create analytics session (best-effort) ─────
    await _record_view(ar_content, request, db)

    # ── Assemble response ────────────────────────────────────────────
    expires_at_str = expiry_date.isoformat() if hasattr(expiry_date, "isoformat") else str(expiry_date)
    video_payload = ViewerManifestVideo(
        id=video.id,
        title=video.filename or "video",
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


async def _record_view(ar_content: ARContent, request: Request, db: AsyncSession) -> None:
    """Increment ``views_count`` and persist an ``ARViewSession`` (best-effort)."""
    import uuid as _uuid

    try:
        ar_content.views_count = (ar_content.views_count or 0) + 1

        ua_string = request.headers.get("user-agent", "")
        device_type, browser_name, os_name = _parse_user_agent(ua_string)

        ip_address = request.client.host if request.client else None
        session = ARViewSession(
            ar_content_id=ar_content.id,
            project_id=ar_content.project_id,
            company_id=ar_content.company_id,
            session_id=str(_uuid.uuid4()),
            user_agent=ua_string[:500] if ua_string else None,
            device_type=device_type,
            browser=browser_name,
            os=os_name,
            ip_address=ip_address,
            video_played=True,
        )
        db.add(session)
        await db.commit()
        await db.refresh(ar_content)
        logger.info(
            "viewer_manifest_views_incremented",
            ar_content_id=ar_content.id,
            views_count=ar_content.views_count,
        )
    except Exception as exc:
        logger.warning("failed_to_increment_views_manifest", error=str(exc))
        try:
            await db.rollback()
        except Exception:
            pass


def _parse_user_agent(ua_string: str) -> tuple[str, str, str]:
    """Return ``(device_type, browser_name, os_name)`` from a User-Agent string."""
    device_type = "unknown"
    browser_name = "unknown"
    os_name = "unknown"

    if not ua_string:
        return device_type, browser_name, os_name

    ua_lower = ua_string.lower()

    # Device type
    if "android" in ua_lower or "mobile" in ua_lower:
        device_type = "mobile"
    elif "ipad" in ua_lower or "tablet" in ua_lower:
        device_type = "tablet"
    elif "windows" in ua_lower or "macintosh" in ua_lower or "linux" in ua_lower:
        device_type = "desktop"

    # OS
    if "android" in ua_lower:
        os_name = "Android"
    elif "iphone" in ua_lower or "ipad" in ua_lower:
        os_name = "iOS"
    elif "windows" in ua_lower:
        os_name = "Windows"
    elif "macintosh" in ua_lower or "mac os" in ua_lower:
        os_name = "macOS"
    elif "linux" in ua_lower:
        os_name = "Linux"

    # Browser
    if "vertexar" in ua_lower or "arcore" in ua_lower:
        browser_name = "Vertex AR App"
    elif "chrome" in ua_lower and "safari" in ua_lower:
        browser_name = "Chrome"
    elif "firefox" in ua_lower:
        browser_name = "Firefox"
    elif "safari" in ua_lower:
        browser_name = "Safari"

    return device_type, browser_name, os_name