from typing import Optional, List
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from datetime import datetime, timedelta
import re

from app.core.database import get_db, AsyncSessionLocal
from app.models.video import Video
from app.models.ar_content import ARContent
from app.models.video_schedule import VideoSchedule as VideoScheduleModel
from app.schemas.video_schedule import (
    VideoScheduleCreate, VideoScheduleUpdate, VideoSchedule as VideoScheduleSchema,
    VideoSubscriptionUpdate, VideoRotationUpdate, VideoSetActiveResponse,
    VideoActiveUpdate, VideoPlaybackModeUpdate,
    VideoStatusResponse
)
from app.services.video_scheduler import (
    get_active_video, compute_video_status, compute_days_remaining,
    get_active_video_schedule, update_rotation_state
)
from app.utils.ar_content import build_ar_content_storage_path, build_public_url
from app.utils.video_utils import (
    validate_video_file, 
    get_video_metadata, 
    save_uploaded_video,
    generate_video_filename
)
from app.services.thumbnail_service import ThumbnailService
from app.enums import VideoStatus


async def _generate_video_thumbnail_task(video_id: int, video_path: str) -> None:
    svc = ThumbnailService()
    result = await svc.generate_video_thumbnail(
        video_path,
        thumbnail_name=f"video_{video_id}_thumb.webp",
    )

    if result.get("status") != "ready":
        async with AsyncSessionLocal() as session:
            v = await session.get(Video, video_id)
            if v:
                v.status = VideoStatus.FAILED
                await session.commit()
        return

    async with AsyncSessionLocal() as session:
        v = await session.get(Video, video_id)
        if not v:
            return
        v.thumbnail_path = result.get("thumbnail_path")
        v.preview_url = result.get("thumbnail_url")
        v.status = VideoStatus.READY
        await session.commit()

router = APIRouter()


def parse_subscription_preset(preset: str) -> datetime:
    """Parse subscription preset like '1y', '2y' to datetime."""
    if preset == '1y':
        return datetime.utcnow() + timedelta(days=365)
    elif preset == '2y':
        return datetime.utcnow() + timedelta(days=730)
    else:
        # Try to parse as ISO date
        try:
            return datetime.fromisoformat(preset.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError(f"Invalid subscription format: {preset}")


@router.post("/ar-content/{content_id}/videos")
async def upload_videos(
    content_id: str,
    videos: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Upload one or multiple videos for AR content.
    
    Args:
        content_id: AR content ID
        videos: List of video files to upload
        db: Database session
        
    Returns:
        List of created video objects with metadata
    """
    import structlog
    logger = structlog.get_logger()
    
    try:
        content_uuid = int(content_id)
        logger.info("video_upload_started", content_id=content_id, videos_count=len(videos))
    except (TypeError, ValueError):
        logger.error("invalid_content_id", content_id=content_id)
        raise HTTPException(status_code=400, detail="content_id must be int")

    # Verify AR content exists and load relations eagerly
    from sqlalchemy.orm import selectinload
    stmt_content = select(ARContent).options(
        selectinload(ARContent.company),
        selectinload(ARContent.project)
    ).where(ARContent.id == content_uuid)
    result_content = await db.execute(stmt_content)
    ar_content = result_content.scalar_one_or_none()
    if not ar_content:
        raise HTTPException(status_code=404, detail="AR content not found")
    
    # Check if this is the first video for this AR content
    existing_videos_count = await db.scalar(
        select(func.count(Video.id)).where(Video.ar_content_id == content_uuid)
    )
    is_first_video = existing_videos_count == 0
    
    # Build storage paths with company and project names
    storage_base_path = build_ar_content_storage_path(
        company_id=ar_content.company_id,
        project_id=ar_content.project_id,
        order_number=ar_content.order_number,
        company_name=ar_content.company.name if ar_content.company else None,
        project_name=ar_content.project.name if ar_content.project else None
    )
    videos_storage_path = storage_base_path / "videos"
    previews_storage_path = storage_base_path / "previews"
    
    created_videos = []
    
    for upload_file in videos:
        # Validate file
        validate_video_file(upload_file)
        
        # Calculate subscription_end based on AR content duration_years
        subscription_end = None
        if ar_content.duration_years:
            subscription_end = datetime.utcnow() + timedelta(days=365 * ar_content.duration_years)
        
        # Create video record first to get ID
        video = Video(
            ar_content_id=content_uuid,
            filename=upload_file.filename,
            status=VideoStatus.PROCESSING,
            rotation_type='none',
            is_active=False,
            subscription_end=subscription_end,
        )
        
        db.add(video)
        await db.flush()  # Get the video ID without committing
        
        # Generate filename and save file
        try:
            filename = generate_video_filename(upload_file.filename, video.id)
            video_path = videos_storage_path / filename
            
            # Save uploaded file
            await save_uploaded_video(upload_file, video_path)
            
            # Extract metadata
            metadata = await get_video_metadata(str(video_path))
            
            # Update video with metadata
            video.video_path = str(video_path)
            video.video_url = build_public_url(video_path)
            video.preview_url = video.video_url
            video.duration = int(metadata["duration"]) if metadata.get("duration") is not None else None
            video.width = metadata.get("width")
            video.height = metadata.get("height")
            video.size_bytes = metadata.get("size_bytes")
            video.mime_type = metadata.get("mime_type")
            
            # If this is the first video, mark it as active
            if is_first_video and len(created_videos) == 0:
                video.is_active = True
                ar_content.active_video_id = video.id
            
            # Commit this video
            await db.commit()
            await db.refresh(video)
            
            # Enqueue preview generation task
            if background_tasks is not None and video.video_path:
                background_tasks.add_task(_generate_video_thumbnail_task, video.id, str(video_path))
            
            created_videos.append({
                "id": video.id,
                "title": video.filename,
                "video_url": video.video_url,
                "video_path": video.video_path,
                "thumbnail_url": video.preview_url,
                "preview_url": video.preview_url,
                "duration": video.duration,
                "width": video.width,
                "height": video.height,
                "size_bytes": video.size_bytes,
                "mime_type": video.mime_type,
                "status": video.status,
                "is_active": video.is_active,
                "rotation_type": video.rotation_type,
                "created_at": video.created_at,
                "updated_at": video.updated_at,
            })
            
        except Exception as e:
            # Rollback this video's transaction
            await db.rollback()
            logger.error("video_upload_failed", 
                        content_id=content_id, 
                        filename=upload_file.filename, 
                        error=str(e), 
                        exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process video {upload_file.filename}: {str(e)}"
            )
    
    logger.info("video_upload_completed", content_id=content_id, videos_count=len(created_videos))
    return {
        "message": f"Successfully uploaded {len(created_videos)} video(s)",
        "videos": created_videos,
        "ar_content": {
            "id": ar_content.id,
            "active_video_id": ar_content.active_video_id
        }
    }


@router.get("/ar-content/{content_id}/videos", response_model=List[VideoStatusResponse])
async def list_videos(
    content_id: str,
    db: AsyncSession = Depends(get_db),
    include_schedules: bool = Query(False, description="Include full schedule details")
):
    """Get all videos for AR content with computed status and schedule info."""
    try:
        content_uuid = int(content_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="content_id must be int")

    # Verify AR content exists
    ar_content = await db.get(ARContent, content_uuid)
    if not ar_content:
        raise HTTPException(status_code=404, detail="AR content not found")
    
    # Get all videos for this AR content
    stmt = select(Video).where(Video.ar_content_id == content_uuid).order_by(Video.rotation_order.asc(), Video.id.asc())
    result = await db.execute(stmt)
    videos = result.scalars().all()
    
    video_responses = []
    for video in videos:
        # Get schedules for this video
        schedules_stmt = select(VideoScheduleModel).where(VideoScheduleModel.video_id == video.id)
        schedules_result = await db.execute(schedules_stmt)
        schedules = schedules_result.scalars().all()
        
        # Compute status and days remaining
        now = datetime.utcnow()
        status = compute_video_status(video, now)
        days_remaining = compute_days_remaining(video, now)
        
        # Build schedules summary
        schedules_summary = []
        for schedule in schedules:
            schedules_summary.append({
                "id": schedule.id,
                "start_time": schedule.start_time,
                "end_time": schedule.end_time,
                "status": schedule.status,
                "description": schedule.description
            })
        
        video_responses.append({
            "id": video.id,
            "title": video.filename,
            "video_url": video.video_url,
            "preview_url": video.preview_url,
            "is_active": video.is_active,
            "rotation_type": video.rotation_type,
            "subscription_end": video.subscription_end,
            "status": status,
            "days_remaining": days_remaining,
            "schedules_count": len(schedules),
            "schedules_summary": schedules_summary if include_schedules else []
        })
    
    return video_responses


@router.patch("/ar-content/{content_id}/videos/{video_id}/set-active", response_model=VideoSetActiveResponse)
async def set_video_active(
    content_id: str,
    video_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Atomically set a video as the active one for AR content."""
    try:
        content_uuid = int(content_id)
        video_uuid = int(video_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="content_id and video_id must be int")

    # Verify AR content exists
    ar_content = await db.get(ARContent, content_uuid)
    if not ar_content:
        raise HTTPException(status_code=404, detail="AR content not found")
    
    # Verify video exists and belongs to this AR content
    video = await db.get(Video, video_uuid)
    if not video or video.ar_content_id != content_uuid:
        raise HTTPException(status_code=404, detail="Video not found or doesn't belong to this AR content")
    
    try:
        # Clear is_active flag for all other videos in this AR content
        await db.execute(
            select(Video).where(
                and_(
                    Video.ar_content_id == content_uuid,
                    Video.id != video_uuid
                )
            )
        )
        
        # Set all videos as inactive first
        stmt_clear = (
            Video.__table__
            .update()
            .where(Video.ar_content_id == content_uuid)
            .values(is_active=False)
        )
        await db.execute(stmt_clear)
        
        # Set the target video as active
        video.is_active = True
        ar_content.active_video_id = video_uuid
        ar_content.rotation_state = 0  # Reset rotation state
        
        await db.commit()
        
        return VideoSetActiveResponse(
            status="success",
            active_video_id=video_uuid,
            message=f"Video {video_uuid} is now the active video for AR content {content_uuid}"
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to set active video: {str(e)}")


@router.patch("/ar-content/{content_id}/videos/{video_id}/subscription")
async def update_video_subscription(
    content_id: str,
    video_id: str,
    subscription_data: VideoSubscriptionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update video subscription end date."""
    try:
        content_uuid = int(content_id)
        video_uuid = int(video_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="content_id and video_id must be int")

    # Verify AR content exists
    ar_content = await db.get(ARContent, content_uuid)
    if not ar_content:
        raise HTTPException(status_code=404, detail="AR content not found")
    
    # Verify video exists and belongs to this AR content
    video = await db.get(Video, video_uuid)
    if not video or video.ar_content_id != content_uuid:
        raise HTTPException(status_code=404, detail="Video not found or doesn't belong to this AR content")
    
    try:
        # Parse subscription date
        subscription_end = parse_subscription_preset(subscription_data.subscription)
        
        # Update subscription
        video.subscription_end = subscription_end
        
        # If subscription is already in the past, deactivate video
        if subscription_end <= datetime.utcnow():
            video.is_active = False
            # If this was the active video, clear it
            if ar_content.active_video_id == video_uuid:
                ar_content.active_video_id = None
        
        await db.commit()
        
        return {
            "status": "updated",
            "subscription_end": subscription_end,
            "is_active": video.is_active,
            "message": f"Subscription updated for video {video_uuid}"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update subscription: {str(e)}")


@router.patch("/ar-content/{content_id}/videos/{video_id}/rotation")
async def update_video_rotation(
    content_id: str,
    video_id: str,
    rotation_data: VideoRotationUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update video rotation type and reset rotation state."""
    try:
        content_uuid = int(content_id)
        video_uuid = int(video_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="content_id and video_id must be int")

    # Verify AR content exists
    ar_content = await db.get(ARContent, content_uuid)
    if not ar_content:
        raise HTTPException(status_code=404, detail="AR content not found")
    
    # Verify video exists and belongs to this AR content
    video = await db.get(Video, video_uuid)
    if not video or video.ar_content_id != content_uuid:
        raise HTTPException(status_code=404, detail="Video not found or doesn't belong to this AR content")
    
    try:
        # Validate rotation type
        valid_types = ["none", "sequential", "cyclic"]
        if rotation_data.rotation_type not in valid_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid rotation type. Must be one of: {', '.join(valid_types)}"
            )
        
        # Update rotation type
        video.rotation_type = rotation_data.rotation_type
        
        # Reset rotation state for the AR content so viewer starts at index 0
        if rotation_data.rotation_type != "none":
            ar_content.rotation_state = 0
        
        await db.commit()
        
        return {
            "status": "updated",
            "rotation_type": rotation_data.rotation_type,
            "rotation_state": ar_content.rotation_state,
            "message": f"Rotation type updated to '{rotation_data.rotation_type}' for video {video_uuid}"
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update rotation: {str(e)}")


@router.patch("/ar-content/{content_id}/videos/{video_id}/active")
async def update_video_active_flag(
    content_id: str,
    video_id: str,
    active_data: VideoActiveUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Toggle video active flag for rotation/scheduling."""
    import structlog
    log = structlog.get_logger()

    try:
        content_uuid = int(content_id)
        video_uuid = int(video_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="content_id and video_id must be int")

    ar_content = await db.get(ARContent, content_uuid)
    if not ar_content:
        raise HTTPException(status_code=404, detail="AR content not found")

    video = await db.get(Video, video_uuid)
    if not video or video.ar_content_id != content_uuid:
        raise HTTPException(status_code=404, detail="Video not found or doesn't belong to this AR content")

    try:
        video.is_active = bool(active_data.is_active)
        if not video.is_active and ar_content.active_video_id == video_uuid:
            ar_content.active_video_id = None

        await db.commit()
        await db.refresh(video)

        return {
            "status": "updated",
            "video_id": video.id,
            "is_active": video.is_active
        }
    except Exception as exc:
        await db.rollback()
        log.error("update_video_active_failed", error=str(exc), content_id=content_id, video_id=video_id)
        raise HTTPException(status_code=500, detail=f"Failed to update video active flag: {str(exc)}")


@router.patch("/ar-content/{content_id}/playback-mode")
async def update_playback_mode(
    content_id: str,
    mode_data: VideoPlaybackModeUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Switch playback mode between manual and automatic rotation."""
    import structlog
    log = structlog.get_logger()

    try:
        content_uuid = int(content_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="content_id must be int")

    ar_content = await db.get(ARContent, content_uuid)
    if not ar_content:
        raise HTTPException(status_code=404, detail="AR content not found")

    stmt = select(Video).where(Video.ar_content_id == content_uuid).order_by(Video.id.asc())
    result = await db.execute(stmt)
    videos = list(result.scalars().all())
    if not videos:
        raise HTTPException(status_code=400, detail="No videos found for this AR content")

    try:
        if mode_data.mode == "manual":
            if not mode_data.active_video_id:
                raise HTTPException(status_code=400, detail="active_video_id is required for manual mode")

            target = next((v for v in videos if v.id == mode_data.active_video_id), None)
            if not target:
                raise HTTPException(status_code=404, detail="Active video not found for this AR content")

            for v in videos:
                v.is_active = (v.id == target.id)
                v.rotation_type = "none"

            ar_content.active_video_id = target.id
            ar_content.rotation_state = 0
        else:
            active_ids = mode_data.active_video_ids or []
            if not active_ids:
                raise HTTPException(status_code=400, detail="active_video_ids is required for automatic mode")

            active_set = set(active_ids)
            unknown_ids = [vid for vid in active_ids if not any(v.id == vid for v in videos)]
            if unknown_ids:
                raise HTTPException(status_code=404, detail=f"Unknown video IDs: {unknown_ids}")

            for v in videos:
                v.is_active = v.id in active_set
                v.rotation_type = mode_data.mode

            ar_content.active_video_id = None
            ar_content.rotation_state = 0

        await db.commit()

        return {
            "status": "updated",
            "mode": mode_data.mode,
            "active_video_id": ar_content.active_video_id,
            "active_video_ids": [v.id for v in videos if v.is_active]
        }
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        log.error("update_playback_mode_failed", error=str(exc), content_id=content_id)
        raise HTTPException(status_code=500, detail=f"Failed to update playback mode: {str(exc)}")


# Schedule CRUD endpoints
@router.get("/ar-content/{content_id}/videos/{video_id}/schedules", response_model=List[VideoScheduleSchema])
async def list_video_schedules(
    content_id: str,
    video_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all schedules for a video."""
    try:
        content_uuid = int(content_id)
        video_uuid = int(video_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="content_id and video_id must be int")

    # Verify video exists and belongs to this AR content
    video = await db.get(Video, video_uuid)
    if not video or video.ar_content_id != content_uuid:
        raise HTTPException(status_code=404, detail="Video not found or doesn't belong to this AR content")
    
    stmt = select(VideoScheduleModel).where(VideoScheduleModel.video_id == video_uuid).order_by(VideoScheduleModel.start_time.asc())
    result = await db.execute(stmt)
    schedules = result.scalars().all()
    
    return schedules


@router.post("/ar-content/{content_id}/videos/{video_id}/schedules", response_model=VideoScheduleSchema)
async def create_video_schedule(
    content_id: str,
    video_id: str,
    schedule_data: VideoScheduleCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new schedule for a video."""
    try:
        content_uuid = int(content_id)
        video_uuid = int(video_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="content_id and video_id must be int")

    # Verify video exists and belongs to this AR content
    video = await db.get(Video, video_uuid)
    if not video or video.ar_content_id != content_uuid:
        raise HTTPException(status_code=404, detail="Video not found or doesn't belong to this AR content")
    
    # Validate time range
    if schedule_data.start_time >= schedule_data.end_time:
        raise HTTPException(status_code=400, detail="Start time must be before end time")
    
    try:
        # Check for overlapping schedules
        overlap_stmt = select(VideoScheduleModel).where(
            and_(
                VideoScheduleModel.video_id == video_uuid,
                or_(
                    # New schedule starts during existing schedule
                    and_(
                        VideoScheduleModel.start_time <= schedule_data.start_time,
                        VideoScheduleModel.end_time > schedule_data.start_time
                    ),
                    # New schedule ends during existing schedule
                    and_(
                        VideoScheduleModel.start_time < schedule_data.end_time,
                        VideoScheduleModel.end_time >= schedule_data.end_time
                    ),
                    # New schedule completely contains existing schedule
                    and_(
                        VideoScheduleModel.start_time >= schedule_data.start_time,
                        VideoScheduleModel.end_time <= schedule_data.end_time
                    )
                )
            )
        )
        
        existing_schedules = await db.execute(overlap_stmt)
        if existing_schedules.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Schedule overlaps with existing schedule")
        
        # Create new schedule
        schedule = VideoScheduleModel(
            video_id=video_uuid,
            start_time=schedule_data.start_time,
            end_time=schedule_data.end_time,
            description=schedule_data.description,
        )
        
        db.add(schedule)
        await db.commit()
        await db.refresh(schedule)
        
        return schedule
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create schedule: {str(e)}")


@router.patch("/ar-content/{content_id}/videos/{video_id}/schedules/{schedule_id}", response_model=VideoScheduleSchema)
async def update_video_schedule(
    content_id: str,
    video_id: str,
    schedule_id: str,
    schedule_data: VideoScheduleUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an existing schedule."""
    try:
        content_uuid = int(content_id)
        video_uuid = int(video_id)
        schedule_uuid = int(schedule_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="content_id, video_id, schedule_id must be int")

    # Verify video exists and belongs to this AR content
    video = await db.get(Video, video_uuid)
    if not video or video.ar_content_id != content_uuid:
        raise HTTPException(status_code=404, detail="Video not found or doesn't belong to this AR content")
    
    # Get existing schedule
    schedule = await db.get(VideoScheduleModel, schedule_uuid)
    if not schedule or schedule.video_id != video_uuid:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    try:
        # Update fields if provided
        if schedule_data.start_time is not None:
            schedule.start_time = schedule_data.start_time
        if schedule_data.end_time is not None:
            schedule.end_time = schedule_data.end_time
        if schedule_data.description is not None:
            schedule.description = schedule_data.description
        
        # Validate time range
        if schedule.start_time >= schedule.end_time:
            raise HTTPException(status_code=400, detail="Start time must be before end time")
        
        # Check for overlapping schedules (excluding this one)
        overlap_stmt = select(VideoScheduleModel).where(
            and_(
                VideoScheduleModel.video_id == video_uuid,
                VideoScheduleModel.id != schedule_uuid,
                or_(
                    # Updated schedule starts during existing schedule
                    and_(
                        VideoScheduleModel.start_time <= schedule.start_time,
                        VideoScheduleModel.end_time > schedule.start_time
                    ),
                    # Updated schedule ends during existing schedule
                    and_(
                        VideoScheduleModel.start_time < schedule.end_time,
                        VideoScheduleModel.end_time >= schedule.end_time
                    ),
                    # Updated schedule completely contains existing schedule
                    and_(
                        VideoScheduleModel.start_time >= schedule.start_time,
                        VideoScheduleModel.end_time <= schedule.end_time
                    )
                )
            )
        )
        
        existing_schedules = await db.execute(overlap_stmt)
        if existing_schedules.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Schedule overlaps with existing schedule")
        
        await db.commit()
        await db.refresh(schedule)
        
        return schedule
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update schedule: {str(e)}")


@router.delete("/ar-content/{content_id}/videos/{video_id}/schedules/{schedule_id}")
async def delete_video_schedule(
    content_id: str,
    video_id: str,
    schedule_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a schedule."""
    try:
        content_uuid = int(content_id)
        video_uuid = int(video_id)
        schedule_uuid = int(schedule_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="content_id, video_id, schedule_id must be int")

    # Verify video exists and belongs to this AR content
    video = await db.get(Video, video_uuid)
    if not video or video.ar_content_id != content_uuid:
        raise HTTPException(status_code=404, detail="Video not found or doesn't belong to this AR content")
    
    # Get existing schedule
    schedule = await db.get(VideoScheduleModel, schedule_uuid)
    if not schedule or schedule.video_id != video_uuid:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    try:
        await db.delete(schedule)
        await db.commit()
        
        return {"status": "deleted", "message": f"Schedule {schedule_uuid} deleted"}
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete schedule: {str(e)}")


# Legacy endpoints (kept for backward compatibility)
@router.put("/videos/{video_id}")
async def update_video(video_id: str, payload: dict, db: AsyncSession = Depends(get_db)):
    """Legacy endpoint - use specific PATCH endpoints instead."""
    try:
        video_uuid = int(video_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="video_id must be int")

    v = await db.get(Video, video_uuid)
    if not v:
        raise HTTPException(status_code=404, detail="Video not found")
    for k, val in payload.items():
        if hasattr(v, k):
            setattr(v, k, val)
    await db.commit()
    return {"status": "updated"}


@router.delete("/videos/{video_id}")
async def delete_video(video_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a video and all its schedules."""
    try:
        video_uuid = int(video_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="video_id must be int")

    v = await db.get(Video, video_uuid)
    if not v:
        raise HTTPException(status_code=404, detail="Video not found")
    await db.delete(v)
    await db.commit()
    return {"status": "deleted"}