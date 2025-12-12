from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from datetime import datetime, timedelta
import re

from app.core.database import get_db
from app.models.video import Video
from app.models.ar_content import ARContent
from app.models.video_schedule import VideoSchedule
from app.schemas.video_schedule import (
    VideoScheduleCreate, VideoScheduleUpdate, VideoSchedule,
    VideoSubscriptionUpdate, VideoRotationUpdate, VideoSetActiveResponse,
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
from app.tasks.preview_tasks import generate_video_thumbnail

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
    content_id: int,
    videos: List[UploadFile] = File(...),
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
    # Verify AR content exists
    ar_content = await db.get(ARContent, content_id)
    if not ar_content:
        raise HTTPException(status_code=404, detail="AR content not found")
    
    # Check if this is the first video for this AR content
    existing_videos_count = await db.scalar(
        select(func.count(Video.id)).where(Video.ar_content_id == content_id)
    )
    is_first_video = existing_videos_count == 0
    
    # Build storage paths
    storage_base_path = build_ar_content_storage_path(
        ar_content.company_id, 
        ar_content.project_id, 
        ar_content.unique_id
    )
    videos_storage_path = storage_base_path / "videos"
    previews_storage_path = storage_base_path / "previews"
    
    created_videos = []
    
    for upload_file in videos:
        # Validate file
        validate_video_file(upload_file)
        
        # Create video record first to get ID
        video = Video(
            ar_content_id=content_id,
            title=upload_file.filename,
            status="processing",
            rotation_type='none',
            is_active=False,  # Will be updated for first video
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
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
            video.duration = metadata["duration"]
            video.width = metadata["width"]
            video.height = metadata["height"]
            video.size_bytes = metadata["size_bytes"]
            video.mime_type = metadata["mime_type"]
            
            # If this is the first video, mark it as active
            if is_first_video and len(created_videos) == 0:
                video.is_active = True
                ar_content.active_video_id = video.id
            
            # Commit this video
            await db.commit()
            await db.refresh(video)
            
            # Enqueue preview generation task
            try:
                generate_video_thumbnail.delay(video.id)
            except Exception as e:
                # Log error but don't fail the upload
                import structlog
                logger = structlog.get_logger()
                logger.error("preview_task_enqueue_failed", video_id=video.id, error=str(e))
            
            created_videos.append({
                "id": video.id,
                "title": video.title,
                "video_url": video.video_url,
                "video_path": video.video_path,
                "thumbnail_url": video.thumbnail_url,
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
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process video {upload_file.filename}: {str(e)}"
            )
    
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
    content_id: int, 
    db: AsyncSession = Depends(get_db),
    include_schedules: bool = Query(False, description="Include full schedule details")
):
    """Get all videos for AR content with computed status and schedule info."""
    # Verify AR content exists
    ar_content = await db.get(ARContent, content_id)
    if not ar_content:
        raise HTTPException(status_code=404, detail="AR content not found")
    
    # Get all videos for this AR content
    stmt = select(Video).where(Video.ar_content_id == content_id).order_by(Video.rotation_order.asc(), Video.id.asc())
    result = await db.execute(stmt)
    videos = result.scalars().all()
    
    video_responses = []
    for video in videos:
        # Get schedules for this video
        schedules_stmt = select(VideoSchedule).where(VideoSchedule.video_id == video.id)
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
            "title": video.title,
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
    content_id: int,
    video_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Atomically set a video as the active one for AR content."""
    # Verify AR content exists
    ar_content = await db.get(ARContent, content_id)
    if not ar_content:
        raise HTTPException(status_code=404, detail="AR content not found")
    
    # Verify video exists and belongs to this AR content
    video = await db.get(Video, video_id)
    if not video or video.ar_content_id != content_id:
        raise HTTPException(status_code=404, detail="Video not found or doesn't belong to this AR content")
    
    try:
        # Clear is_active flag for all other videos in this AR content
        await db.execute(
            select(Video).where(
                and_(
                    Video.ar_content_id == content_id,
                    Video.id != video_id
                )
            )
        )
        
        # Set all videos as inactive first
        stmt_clear = (
            Video.__table__
            .update()
            .where(Video.ar_content_id == content_id)
            .values(is_active=False)
        )
        await db.execute(stmt_clear)
        
        # Set the target video as active
        video.is_active = True
        ar_content.active_video_id = video_id
        ar_content.rotation_state = 0  # Reset rotation state
        
        await db.commit()
        
        return VideoSetActiveResponse(
            status="success",
            active_video_id=video_id,
            message=f"Video {video_id} is now the active video for AR content {content_id}"
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to set active video: {str(e)}")


@router.patch("/ar-content/{content_id}/videos/{video_id}/subscription")
async def update_video_subscription(
    content_id: int,
    video_id: int,
    subscription_data: VideoSubscriptionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update video subscription end date."""
    # Verify AR content exists
    ar_content = await db.get(ARContent, content_id)
    if not ar_content:
        raise HTTPException(status_code=404, detail="AR content not found")
    
    # Verify video exists and belongs to this AR content
    video = await db.get(Video, video_id)
    if not video or video.ar_content_id != content_id:
        raise HTTPException(status_code=404, detail="Video not found or doesn't belong to this AR content")
    
    try:
        # Parse subscription date
        subscription_end = parse_subscription_preset(subscription_data.subscription)
        
        # Update subscription
        video.subscription_end = subscription_end
        video.updated_at = datetime.utcnow()
        
        # If subscription is already in the past, deactivate video
        if subscription_end <= datetime.utcnow():
            video.is_active = False
            # If this was the active video, clear it
            if ar_content.active_video_id == video_id:
                ar_content.active_video_id = None
        
        await db.commit()
        
        return {
            "status": "updated",
            "subscription_end": subscription_end,
            "is_active": video.is_active,
            "message": f"Subscription updated for video {video_id}"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update subscription: {str(e)}")


@router.patch("/ar-content/{content_id}/videos/{video_id}/rotation")
async def update_video_rotation(
    content_id: int,
    video_id: int,
    rotation_data: VideoRotationUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update video rotation type and reset rotation state."""
    # Verify AR content exists
    ar_content = await db.get(ARContent, content_id)
    if not ar_content:
        raise HTTPException(status_code=404, detail="AR content not found")
    
    # Verify video exists and belongs to this AR content
    video = await db.get(Video, video_id)
    if not video or video.ar_content_id != content_id:
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
        video.updated_at = datetime.utcnow()
        
        # Reset rotation state for the AR content so viewer starts at index 0
        if rotation_data.rotation_type != "none":
            ar_content.rotation_state = 0
        
        await db.commit()
        
        return {
            "status": "updated",
            "rotation_type": rotation_data.rotation_type,
            "rotation_state": ar_content.rotation_state,
            "message": f"Rotation type updated to '{rotation_data.rotation_type}' for video {video_id}"
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update rotation: {str(e)}")


# Schedule CRUD endpoints
@router.get("/ar-content/{content_id}/videos/{video_id}/schedules", response_model=List[VideoSchedule])
async def list_video_schedules(
    content_id: int,
    video_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get all schedules for a video."""
    # Verify video exists and belongs to this AR content
    video = await db.get(Video, video_id)
    if not video or video.ar_content_id != content_id:
        raise HTTPException(status_code=404, detail="Video not found or doesn't belong to this AR content")
    
    stmt = select(VideoSchedule).where(VideoSchedule.video_id == video_id).order_by(VideoSchedule.start_time.asc())
    result = await db.execute(stmt)
    schedules = result.scalars().all()
    
    return schedules


@router.post("/ar-content/{content_id}/videos/{video_id}/schedules", response_model=VideoSchedule)
async def create_video_schedule(
    content_id: int,
    video_id: int,
    schedule_data: VideoScheduleCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new schedule for a video."""
    # Verify video exists and belongs to this AR content
    video = await db.get(Video, video_id)
    if not video or video.ar_content_id != content_id:
        raise HTTPException(status_code=404, detail="Video not found or doesn't belong to this AR content")
    
    # Validate time range
    if schedule_data.start_time >= schedule_data.end_time:
        raise HTTPException(status_code=400, detail="Start time must be before end time")
    
    try:
        # Check for overlapping schedules
        overlap_stmt = select(VideoSchedule).where(
            and_(
                VideoSchedule.video_id == video_id,
                or_(
                    # New schedule starts during existing schedule
                    and_(
                        VideoSchedule.start_time <= schedule_data.start_time,
                        VideoSchedule.end_time > schedule_data.start_time
                    ),
                    # New schedule ends during existing schedule
                    and_(
                        VideoSchedule.start_time < schedule_data.end_time,
                        VideoSchedule.end_time >= schedule_data.end_time
                    ),
                    # New schedule completely contains existing schedule
                    and_(
                        VideoSchedule.start_time >= schedule_data.start_time,
                        VideoSchedule.end_time <= schedule_data.end_time
                    )
                )
            )
        )
        
        existing_schedules = await db.execute(overlap_stmt)
        if existing_schedules.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Schedule overlaps with existing schedule")
        
        # Create new schedule
        schedule = VideoSchedule(
            video_id=video_id,
            start_time=schedule_data.start_time,
            end_time=schedule_data.end_time,
            description=schedule_data.description,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
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


@router.patch("/ar-content/{content_id}/videos/{video_id}/schedules/{schedule_id}", response_model=VideoSchedule)
async def update_video_schedule(
    content_id: int,
    video_id: int,
    schedule_id: int,
    schedule_data: VideoScheduleUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an existing schedule."""
    # Verify video exists and belongs to this AR content
    video = await db.get(Video, video_id)
    if not video or video.ar_content_id != content_id:
        raise HTTPException(status_code=404, detail="Video not found or doesn't belong to this AR content")
    
    # Get existing schedule
    schedule = await db.get(VideoSchedule, schedule_id)
    if not schedule or schedule.video_id != video_id:
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
        overlap_stmt = select(VideoSchedule).where(
            and_(
                VideoSchedule.video_id == video_id,
                VideoSchedule.id != schedule_id,
                or_(
                    # Updated schedule starts during existing schedule
                    and_(
                        VideoSchedule.start_time <= schedule.start_time,
                        VideoSchedule.end_time > schedule.start_time
                    ),
                    # Updated schedule ends during existing schedule
                    and_(
                        VideoSchedule.start_time < schedule.end_time,
                        VideoSchedule.end_time >= schedule.end_time
                    ),
                    # Updated schedule completely contains existing schedule
                    and_(
                        VideoSchedule.start_time >= schedule.start_time,
                        VideoSchedule.end_time <= schedule.end_time
                    )
                )
            )
        )
        
        existing_schedules = await db.execute(overlap_stmt)
        if existing_schedules.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Schedule overlaps with existing schedule")
        
        schedule.updated_at = datetime.utcnow()
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
    content_id: int,
    video_id: int,
    schedule_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a schedule."""
    # Verify video exists and belongs to this AR content
    video = await db.get(Video, video_id)
    if not video or video.ar_content_id != content_id:
        raise HTTPException(status_code=404, detail="Video not found or doesn't belong to this AR content")
    
    # Get existing schedule
    schedule = await db.get(VideoSchedule, schedule_id)
    if not schedule or schedule.video_id != video_id:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    try:
        await db.delete(schedule)
        await db.commit()
        
        return {"status": "deleted", "message": f"Schedule {schedule_id} deleted"}
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete schedule: {str(e)}")


# Legacy endpoints (kept for backward compatibility)
@router.put("/videos/{video_id}")
async def update_video(video_id: int, payload: dict, db: AsyncSession = Depends(get_db)):
    """Legacy endpoint - use specific PATCH endpoints instead."""
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
    """Delete a video and all its schedules."""
    v = await db.get(Video, video_id)
    if not v:
        raise HTTPException(status_code=404, detail="Video not found")
    await db.delete(v)
    await db.commit()
    return {"status": "deleted"}