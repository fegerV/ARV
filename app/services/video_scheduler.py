from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ar_content import ARContent
from app.models.video import Video
from app.models.video_schedule import VideoSchedule


def compute_video_status(video: Video, now: datetime = None) -> str:
    """Compute video status based on subscription and active state."""
    if now is None:
        now = datetime.utcnow()
    
    if not video.is_active:
        return "inactive"
    
    if video.subscription_end and video.subscription_end <= now:
        return "expired"
    
    if video.subscription_end:
        days_remaining = (video.subscription_end - now).days
        if days_remaining <= 7:
            return "expiring"
    
    return "active"


def compute_days_remaining(video: Video, now: datetime = None) -> Optional[int]:
    """Compute days remaining until subscription expires."""
    if now is None:
        now = datetime.utcnow()
    
    if not video.subscription_end:
        return None
    
    if video.subscription_end <= now:
        return 0
    
    return (video.subscription_end - now).days


async def get_active_video_schedule(video_id: int, db: AsyncSession, now: datetime = None) -> Optional[VideoSchedule]:
    """Get the currently active schedule for a video."""
    if now is None:
        now = datetime.utcnow()
    
    stmt = select(VideoSchedule).where(
        and_(
            VideoSchedule.video_id == video_id,
            VideoSchedule.start_time <= now,
            VideoSchedule.end_time >= now,
            VideoSchedule.status == "active"
        )
    )
    
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_videos_with_active_schedules(ar_content_id: int, db: AsyncSession, now: datetime = None) -> list[Video]:
    """Get all videos for AR content that have active schedules right now."""
    if now is None:
        now = datetime.utcnow()
    
    stmt = select(Video).distinct().join(VideoSchedule).where(
        and_(
            Video.ar_content_id == ar_content_id,
            Video.is_active == True,
            VideoSchedule.start_time <= now,
            VideoSchedule.end_time >= now,
            VideoSchedule.status == "active"
        )
    )
    
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_next_rotation_video(ar_content: ARContent, db: AsyncSession, now: datetime = None) -> Optional[Video]:
    """Get the next video based on rotation type and current state."""
    if now is None:
        now = datetime.utcnow()
    
    # Get all active videos for this AR content, ordered by rotation_order
    stmt = select(Video).where(
        and_(
            Video.ar_content_id == ar_content.id,
            Video.is_active == True
        )
    ).order_by(Video.rotation_order.asc(), Video.id.asc())
    
    result = await db.execute(stmt)
    videos = list(result.scalars().all())
    
    # Filter out expired subscriptions
    active_videos = [
        v for v in videos 
        if not v.subscription_end or v.subscription_end > now
    ]
    
    if not active_videos:
        return None
    
    if ar_content.rotation_state is None:
        ar_content.rotation_state = 0
    
    current_index = ar_content.rotation_state % len(active_videos)
    
    # Handle different rotation types
    if len(active_videos) == 1:
        return active_videos[0]
    
    # Get the first active video to determine rotation type
    rotation_type = active_videos[0].rotation_type
    
    if rotation_type == "none":
        # For 'none', always return the first one
        return active_videos[0]
    elif rotation_type == "sequential":
        # For 'sequential', return current video based on rotation_state
        # Don't wrap around - stay at last video
        # rotation_state will be incremented after this call
        if current_index >= len(active_videos):
            return active_videos[-1]
        return active_videos[min(current_index, len(active_videos) - 1)]
    elif rotation_type == "cyclic":
        # For 'cyclic', return current video, then wrap around on next call
        return active_videos[current_index % len(active_videos)]
    else:
        # Default to first video
        return active_videos[0]


async def get_active_video(ar_content_id: int, db: AsyncSession) -> Optional[Dict[str, Any]]:
    """Return the currently active video for AR content with metadata.
    Priority:
    1) Video with currently active schedule window
    2) ARContent.active_video_id (if not expired)
    3) Rotation-based selection
    4) Any active video (fallback)
    
    Returns dict with video info and selection source.
    """
    now = datetime.utcnow()

    # Get AR content
    ar_content = await db.get(ARContent, ar_content_id)
    if not ar_content:
        return None

    # 1) Check for videos with active schedules
    scheduled_videos = await get_videos_with_active_schedules(ar_content_id, db, now)
    if scheduled_videos:
        video = scheduled_videos[0]  # Take the first one
        schedule = await get_active_video_schedule(video.id, db, now)
        
        return {
            "video": video,
            "source": "schedule",
            "schedule_id": schedule.id if schedule else None,
            "expires_in": None  # Schedule-based, not subscription-based
        }

    # 2) ARContent.active_video_id (if not expired)
    if ar_content.active_video_id:
        video = await db.get(Video, ar_content.active_video_id)
        if video and video.is_active:
            # Check subscription
            if not video.subscription_end or video.subscription_end > now:
                expires_in = compute_days_remaining(video, now)
                return {
                    "video": video,
                    "source": "active_default",
                    "schedule_id": None,
                    "expires_in": expires_in
                }

    # 3) Rotation-based selection
    rotation_video = await get_next_rotation_video(ar_content, db, now)
    if rotation_video:
        expires_in = compute_days_remaining(rotation_video, now)
        return {
            "video": rotation_video,
            "source": "rotation",
            "schedule_id": None,
            "expires_in": expires_in
        }

    # 4) Fallback: any active video
    stmt_any = select(Video).where(
        and_(
            Video.ar_content_id == ar_content_id,
            Video.is_active == True
        )
    ).order_by(Video.rotation_order.asc(), Video.id.asc())
    
    result_any = await db.execute(stmt_any)
    fallback_video = result_any.scalar_one_or_none()
    
    if fallback_video:
        # Check subscription
        if not fallback_video.subscription_end or fallback_video.subscription_end > now:
            expires_in = compute_days_remaining(fallback_video, now)
            return {
                "video": fallback_video,
                "source": "fallback",
                "schedule_id": None,
                "expires_in": expires_in
            }

    return None


async def update_rotation_state(ar_content: ARContent, db: AsyncSession) -> None:
    """Update the rotation state for sequential/cyclic rotation."""
    from sqlalchemy import select, and_
    from app.models.video import Video
    
    # Get active videos to check rotation type and count
    stmt = select(Video).where(
        and_(
            Video.ar_content_id == ar_content.id,
            Video.is_active == True
        )
    ).order_by(Video.rotation_order.asc(), Video.id.asc())
    
    result = await db.execute(stmt)
    active_videos = list(result.scalars().all())
    
    if not active_videos:
        return
    
    rotation_type = active_videos[0].rotation_type
    
    # For sequential, don't increment beyond last video
    if rotation_type == "sequential":
        current_state = ar_content.rotation_state or 0
        if current_state < len(active_videos) - 1:
            ar_content.rotation_state = current_state + 1
    elif rotation_type == "cyclic":
        # For cyclic, always increment (will wrap around)
        ar_content.rotation_state = (ar_content.rotation_state or 0) + 1
    
    await db.commit()
