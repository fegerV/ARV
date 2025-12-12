from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime

from app.core.database import get_db
from app.models.video import Video
from app.models.ar_content import ARContent
from app.utils.ar_content import build_ar_content_storage_path, build_public_url
from app.utils.video_utils import (
    validate_video_file, 
    get_video_metadata, 
    save_uploaded_video,
    generate_video_filename
)
from app.tasks.preview_tasks import generate_video_thumbnail

router = APIRouter()


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
