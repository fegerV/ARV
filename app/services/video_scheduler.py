from datetime import datetime, date, timedelta, timezone
from typing import Optional, Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import random
import structlog

from app.models.ar_content import ARContent
from app.models.video import Video
from app.models.video_schedule import VideoSchedule
from app.models.video_rotation_schedule import VideoRotationSchedule

logger = structlog.get_logger()


def compute_video_status(video: Video, now: datetime = None) -> str:
    """Compute video status based on subscription and active state."""
    if now is None:
        now = datetime.now(timezone.utc)
    
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
        now = datetime.now(timezone.utc)
    
    if not video.subscription_end:
        return None
    
    if video.subscription_end <= now:
        return 0
    
    return (video.subscription_end - now).days


async def get_active_video_schedule(video_id: int, db: AsyncSession, now: datetime = None) -> Optional[VideoSchedule]:
    """Get the currently active schedule for a video."""
    if now is None:
        now = datetime.now(timezone.utc)
    
    stmt = select(VideoSchedule).where(
        and_(
            VideoSchedule.video_id == video_id,
            VideoSchedule.start_time.isnot(None),
            VideoSchedule.end_time.isnot(None),
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
        now = datetime.now(timezone.utc)
    
    stmt = select(Video).distinct().join(VideoSchedule).where(
        and_(
            Video.ar_content_id == ar_content_id,
            Video.is_active == True,
            VideoSchedule.start_time.isnot(None),
            VideoSchedule.end_time.isnot(None),
            VideoSchedule.start_time <= now,
            VideoSchedule.end_time >= now,
            VideoSchedule.status == "active"
        )
    )
    
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def check_date_rules(rule: VideoRotationSchedule, check_date: date, db: AsyncSession) -> Optional[Video]:
    """Check if there's a video scheduled for a specific date (highest priority).
    
    Supports both specific dates and recurring dates (e.g., every December 31).
    """
    if not rule.date_rules:
        return None
    
    for date_rule in rule.date_rules:
        rule_date_str = date_rule.get("date")
        if not rule_date_str:
            continue
        
        try:
            # Parse date (handle both "2025-12-31" and "2025-12-31T00:00:00")
            if "T" in rule_date_str:
                rule_date = datetime.fromisoformat(rule_date_str.replace("Z", "+00:00")).date()
            else:
                rule_date = date.fromisoformat(rule_date_str)
            
            # Check if dates match
            is_recurring = date_rule.get("recurring", False)
            
            if is_recurring:
                # For recurring dates, check month and day only
                if rule_date.month == check_date.month and rule_date.day == check_date.day:
                    video_id = date_rule.get("video_id")
                    if video_id:
                        video = await db.get(Video, video_id)
                        if video and video.is_active:
                            # Check subscription
                            now = datetime.now(timezone.utc)
                            if not video.subscription_end or video.subscription_end > now:
                                return video
            else:
                # Exact date match
                if rule_date == check_date:
                    video_id = date_rule.get("video_id")
                    if video_id:
                        video = await db.get(Video, video_id)
                        if video and video.is_active:
                            now = datetime.now(timezone.utc)
                            if not video.subscription_end or video.subscription_end > now:
                                return video
        except (ValueError, TypeError) as e:
            logger.warning("invalid_date_rule", error=str(e), date_rule=date_rule)
            continue
    
    return None


async def get_daily_cycle_video(rule: VideoRotationSchedule, check_date: date, db: AsyncSession) -> Optional[Video]:
    """Get video for daily cycle rotation (rotates every day)."""
    if not rule.video_sequence:
        return None
    
    # Use day of year to determine index (ensures same video on same day)
    day_of_year = check_date.timetuple().tm_yday
    index = (day_of_year - 1) % len(rule.video_sequence)
    
    video_id = rule.video_sequence[index]
    if video_id:
        video = await db.get(Video, video_id)
        if video and video.is_active:
            now = datetime.now(timezone.utc)
            if not video.subscription_end or video.subscription_end > now:
                return video
    
    return None


async def get_weekly_cycle_video(rule: VideoRotationSchedule, check_date: date, db: AsyncSession) -> Optional[Video]:
    """Get video for weekly cycle rotation (different video for each day of week)."""
    if not rule.video_sequence:
        return None
    
    # 0 = Monday, 6 = Sunday
    day_of_week = check_date.weekday()
    index = day_of_week % len(rule.video_sequence)
    
    video_id = rule.video_sequence[index]
    if video_id:
        video = await db.get(Video, video_id)
        if video and video.is_active:
            now = datetime.now(timezone.utc)
            if not video.subscription_end or video.subscription_end > now:
                return video
    
    return None


async def get_random_daily_video(rule: VideoRotationSchedule, check_date: date, db: AsyncSession) -> Optional[Video]:
    """Get random video for the day (seed-based for reproducibility)."""
    if not rule.video_sequence:
        return None
    
    # Get all videos in sequence
    videos = []
    for video_id in rule.video_sequence:
        video = await db.get(Video, video_id)
        if video and video.is_active:
            now = datetime.now(timezone.utc)
            if not video.subscription_end or video.subscription_end > now:
                videos.append(video)
    
    if not videos:
        return None
    
    # Use seed for reproducibility (same date = same video)
    seed_str = f"{rule.random_seed or 'default'}_{check_date.isoformat()}"
    random.seed(seed_str)
    
    # Weighted random selection if videos have rotation_weight
    weights = [getattr(v, 'rotation_weight', 1) for v in videos]
    selected = random.choices(videos, weights=weights, k=1)[0]
    
    return selected


async def get_rotation_rule(ar_content_id: int, db: AsyncSession) -> Optional[VideoRotationSchedule]:
    """Get the active rotation rule for AR content."""
    stmt = select(VideoRotationSchedule).where(
        and_(
            VideoRotationSchedule.ar_content_id == ar_content_id,
            VideoRotationSchedule.is_active == True
        )
    ).order_by(VideoRotationSchedule.created_at.desc())
    
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_default_video(ar_content: ARContent, db: AsyncSession, now: datetime = None) -> Optional[Video]:
    """Get default video for AR content (active_video_id or first active video)."""
    if now is None:
        now = datetime.now(timezone.utc)
    
    # Try active_video_id first
    if ar_content.active_video_id:
        video = await db.get(Video, ar_content.active_video_id)
        if video and video.is_active:
            if not video.subscription_end or video.subscription_end > now:
                return video
    
    # Fallback to first active video
    stmt = select(Video).where(
        and_(
            Video.ar_content_id == ar_content.id,
            Video.is_active == True
        )
    ).order_by(Video.rotation_order.asc(), Video.id.asc())
    
    result = await db.execute(stmt)
    videos = list(result.scalars().all())
    
    for video in videos:
        if not video.subscription_end or video.subscription_end > now:
            return video
    
    return None


async def get_next_rotation_video(ar_content: ARContent, db: AsyncSession, now: datetime = None) -> Optional[Video]:
    """Get the next video based on rotation type and current state (legacy support).
    
    This function maintains backward compatibility with old rotation_type on Video level.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    
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
    
    # Handle different rotation types (legacy)
    if len(active_videos) == 1:
        return active_videos[0]
    
    # Get the first active video to determine rotation type
    rotation_type = active_videos[0].rotation_type
    
    if rotation_type == "none":
        return active_videos[0]
    elif rotation_type == "sequential":
        if current_index >= len(active_videos):
            return active_videos[-1]
        return active_videos[min(current_index, len(active_videos) - 1)]
    elif rotation_type == "cyclic":
        return active_videos[current_index % len(active_videos)]
    else:
        return active_videos[0]


async def get_active_video(ar_content_id: int, db: AsyncSession, override_date: Optional[date] = None) -> Optional[Dict[str, Any]]:
    """Return the currently active video for AR content with metadata.
    
    Priority:
    1) Date-specific rules (holidays, special dates) - highest priority
    2) Video with currently active schedule window
    3) VideoRotationSchedule rule (new architecture)
    4) ARContent.active_video_id (if not expired)
    5) Legacy rotation-based selection (old architecture)
    6) Any active video (fallback)
    
    Args:
        ar_content_id: ID of AR content
        db: Database session
        override_date: Optional date to check (for testing), defaults to today
    
    Returns:
        Dict with video info and selection source, or None if no video available.
    """
    now = datetime.now(timezone.utc)
    check_date = override_date or date.today()

    # Get AR content
    ar_content = await db.get(ARContent, ar_content_id)
    if not ar_content:
        return None

    # 1) Check date-specific rules (highest priority - holidays, special dates)
    rotation_rule = await get_rotation_rule(ar_content_id, db)
    if rotation_rule and rotation_rule.date_rules:
        date_video = await check_date_rules(rotation_rule, check_date, db)
        if date_video:
            return {
                "video": date_video,
                "source": "date_rule",
                "schedule_id": None,
                "expires_in": compute_days_remaining(date_video, now)
            }

    # 2) Check for videos with active schedules (time windows)
    scheduled_videos = await get_videos_with_active_schedules(ar_content_id, db, now)
    if scheduled_videos:
        video = scheduled_videos[0]
        schedule = await get_active_video_schedule(video.id, db, now)
        return {
            "video": video,
            "source": "schedule",
            "schedule_id": schedule.id if schedule else None,
            "expires_in": None
        }

    # 3) Check VideoRotationSchedule rule (new architecture)
    if rotation_rule:
        video = None
        
        match rotation_rule.rotation_type:
            case "fixed":
                # Fixed video - use default_video_id
                if rotation_rule.default_video_id:
                    video = await db.get(Video, rotation_rule.default_video_id)
            
            case "date_specific":
                # Already checked above, but if no match, use default
                if rotation_rule.default_video_id:
                    video = await db.get(Video, rotation_rule.default_video_id)
            
            case "daily_cycle":
                video = await get_daily_cycle_video(rotation_rule, check_date, db)
            
            case "weekly_cycle":
                video = await get_weekly_cycle_video(rotation_rule, check_date, db)
            
            case "random_daily":
                video = await get_random_daily_video(rotation_rule, check_date, db)
            
            case _:
                # Unknown type, use default
                if rotation_rule.default_video_id:
                    video = await db.get(Video, rotation_rule.default_video_id)
        
        if video and video.is_active:
            now_check = datetime.now(timezone.utc)
            if not video.subscription_end or video.subscription_end > now_check:
                expires_in = compute_days_remaining(video, now)
                return {
                    "video": video,
                    "source": "rotation_rule",
                    "schedule_id": None,
                    "expires_in": expires_in
                }

    # 4) ARContent.active_video_id (if not expired)
    if ar_content.active_video_id:
        video = await db.get(Video, ar_content.active_video_id)
        if video and video.is_active:
            if not video.subscription_end or video.subscription_end > now:
                expires_in = compute_days_remaining(video, now)
                return {
                    "video": video,
                    "source": "active_default",
                    "schedule_id": None,
                    "expires_in": expires_in
                }

    # 5) Legacy rotation-based selection (backward compatibility)
    rotation_video = await get_next_rotation_video(ar_content, db, now)
    if rotation_video:
        expires_in = compute_days_remaining(rotation_video, now)
        return {
            "video": rotation_video,
            "source": "rotation",
            "schedule_id": None,
            "expires_in": expires_in
        }

    # 6) Fallback: any active video
    stmt_any = select(Video).where(
        and_(
            Video.ar_content_id == ar_content_id,
            Video.is_active == True
        )
    ).order_by(Video.rotation_order.asc(), Video.id.asc())
    
    result_any = await db.execute(stmt_any)
    fallback_video = result_any.scalar_one_or_none()
    
    if fallback_video:
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
    """Update the rotation state for sequential/cyclic rotation (legacy support)."""
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
