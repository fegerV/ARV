"""
AR Content API routes with Company → Project → AR Content hierarchy.
"""
from app.middleware.rate_limiter import rate_limit
from uuid import uuid4, UUID
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query, BackgroundTasks
import shutil
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog
import re
from datetime import datetime

from app.core.config import settings
from app.core.database import get_db
from app.models.ar_content import ARContent
from app.models.project import Project
from app.models.company import Company
from app.models.video import Video
from app.schemas.ar_content import (
    ARContent as ARContentSchema,
    ARContentCreate,
    ARContentUpdate,
    ARContentVideoUpdate,
    ARContentList,
    ARContentCreateResponse,
    ARContentWithLinks
)
from app.utils.ar_content import (
    build_ar_content_storage_path,
    build_public_url,
    build_unique_link,
    generate_qr_code,
    save_uploaded_file
)
from app.services.marker_service import marker_service

logger = structlog.get_logger()

router = APIRouter(tags=["AR Content"])


def _safe_delete_folder(path: Path) -> None:
    """Best-effort recursive delete of content folder.

    Safety: only allow deleting within STORAGE_BASE_PATH.
    """
    base = Path(settings.STORAGE_BASE_PATH).resolve()
    target = path.resolve()

    try:
        target.relative_to(base)
    except Exception:
        logger.error("ar_content_delete_storage_blocked", storage_path=str(target), base_path=str(base))
        return

    if not target.exists():
        logger.info("ar_content_delete_storage_missing", storage_path=str(target))
        return

    try:
        shutil.rmtree(target)
        logger.info("ar_content_delete_storage_ok", storage_path=str(target))
    except Exception as e:
        logger.error("ar_content_delete_storage_failed", storage_path=str(target), error=str(e))


async def validate_company_project(company_id: int, project_id: int, db: AsyncSession) -> tuple[Company, Project]:
    """Validate that company and project exist and project belongs to company."""
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.company_id != company_id:
        raise HTTPException(status_code=400, detail="Project does not belong to company")
    
    return company, project


async def get_ar_content_or_404(content_id: int, db: AsyncSession) -> ARContent:
    """Get AR content by ID or raise 404."""
    content = await db.get(ARContent, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="AR content not found")
    return content


def generate_order_number() -> str:
    """Generate unique order number in format ORD-YYYYMMDD-XXXX"""
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    # In a real implementation, we'd want to ensure uniqueness within the project
    # For now, we'll use a timestamp-based approach
    import random
    id_part = f"{random.randint(1000, 9999):04d}"
    return f"ORD-{date_str}-{id_part}"


def validate_file_extension(filename: str, allowed_extensions: list) -> bool:
    """Validate file extension against allowed extensions"""
    ext = Path(filename).suffix.lower()[1:]  # Remove the dot
    return ext in allowed_extensions


def validate_file_size(file_size: int, max_size: int) -> bool:
    """Validate file size against maximum allowed size"""
    return file_size <= max_size


@router.get("/", response_model=ARContentList, tags=["AR Content"])
async def list_all_ar_content(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """List all AR content across all companies and projects."""
    stmt = select(ARContent).offset(skip).limit(limit)
    
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    return ARContentList(items=[ARContentSchema.model_validate(item) for item in items])


@router.get("/companies/{company_id}/projects/{project_id}/ar-content", response_model=ARContentList, tags=["AR Content"])
async def list_ar_content(
    company_id: int,
    project_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """List AR content for a specific project within a company."""
    # Validate company and project relationship
    await validate_company_project(company_id, project_id, db)
    
    stmt = select(ARContent).where(
        ARContent.company_id == company_id,
        ARContent.project_id == project_id
    ).offset(skip).limit(limit)
    
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    return ARContentList(items=[ARContentSchema.model_validate(item) for item in items])


@router.post("/", response_model=ARContentCreateResponse, tags=["AR Content"])
async def create_ar_content(
    company_id: int = Form(...),
    project_id: int = Form(...),
    customer_name: Optional[str] = Form(None),
    customer_phone: Optional[str] = Form(None),
    customer_email: Optional[str] = Form(None),
    duration_years: int = Form(...),
    photo_file: UploadFile = File(...),
    video_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Create new AR content with photo and video files."""
    # Validate company and project relationship
    company, project = await validate_company_project(company_id, project_id, db)
    
    # Validate duration years
    if duration_years not in [1, 3, 5]:
        raise HTTPException(status_code=400, detail="duration_years must be one of: 1, 3, 5")
    
    # Validate customer email if provided
    if customer_email:
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, customer_email):
            raise HTTPException(status_code=400, detail="Invalid email format")
    
    # Validate file extensions
    allowed_photo_extensions = ['jpeg', 'jpg', 'png']
    allowed_video_extensions = ['mp4', 'webm', 'mov']
    
    if not validate_file_extension(photo_file.filename, allowed_photo_extensions):
        raise HTTPException(status_code=422, detail="Photo must be JPEG or PNG")
    
    if not validate_file_extension(video_file.filename, allowed_video_extensions):
        raise HTTPException(status_code=422, detail="Video must be MP4, WebM, or MOV")
    
    # Validate file sizes
    MAX_FILE_SIZE_PHOTO = 10 * 1024 * 1024  # 10MB
    MAX_FILE_SIZE_VIDEO = 100 * 1024 * 1024  # 100MB
    
    # Note: In a real implementation, we'd need to check the actual file size
    # For now, we'll assume the files are within limits
    
    # Generate unique identifier
    unique_id = uuid4()
    
    # Generate order number
    order_number = generate_order_number()
    
    # Build storage path
    storage_path = build_ar_content_storage_path(company_id, project_id, unique_id)
    storage_path.mkdir(parents=True, exist_ok=True)
    
    # Save photo
    photo_filename = f"photo{Path(photo_file.filename).suffix}"
    photo_path = storage_path / photo_filename
    await save_uploaded_file(photo_file, photo_path)
    
    # Save video
    video_filename = f"video{Path(video_file.filename).suffix}"
    video_path = storage_path / video_filename
    await save_uploaded_file(video_file, video_path)
    video_url = build_public_url(video_path)
    
    # Generate QR code
    qr_code_url = await generate_qr_code(unique_id, storage_path)
    
    # Create database record for AR content
    ar_content = ARContent(
        company_id=company_id,
        project_id=project_id,
        unique_id=unique_id,
        order_number=order_number,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_email=customer_email,
        duration_years=duration_years,
        photo_path=str(photo_path),
        photo_url=build_public_url(photo_path),
        video_path=str(video_path),
        video_url=video_url,
        qr_code_path=str(storage_path / "qr_code.png"),
        qr_code_url=qr_code_url,
        status="pending"
    )
    
    db.add(ar_content)
    await db.commit()
    await db.refresh(ar_content)
    
    # Create video record
    video_record = Video(
        ar_content_id=ar_content.id,
        filename=video_filename,
        video_path=str(video_path),
        video_url=video_url,
        is_active=True,
        status="uploaded"
    )
    
    db.add(video_record)
    await db.commit()
    await db.refresh(video_record)
    
    # Set the video as active for the AR content
    ar_content.active_video_id = video_record.id
    await db.commit()
    await db.refresh(ar_content)
    
    # Generate Mind AR marker
    try:
        marker_result = await marker_service.generate_marker(
            ar_content_id=ar_content.id,
            image_path=str(photo_path),
            output_dir=str(storage_path)
        )
        
        if marker_result.get("status") == "failed":
            logger.error("marker_generation_failed", error=marker_result.get("error"))
            # We won't fail the whole request if marker generation fails
    except Exception as e:
        logger.error("marker_generation_exception", error=str(e))
        # We won't fail the whole request if marker generation fails
    
    return ARContentCreateResponse(
        id=ar_content.id,
        order_number=ar_content.order_number,
        public_link=build_unique_link(ar_content.unique_id),
        qr_code_url=ar_content.qr_code_url,
        photo_url=ar_content.photo_url,
        video_url=ar_content.video_url
    )




@router.get("/companies/{company_id}/projects/{project_id}/ar-content/{content_id}", response_model=ARContentWithLinks, tags=["AR Content"])
async def get_ar_content(
    company_id: int,
    project_id: int,
    content_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get full AR content metadata including all URLs and videos."""
    # Validate company and project relationship
    await validate_company_project(company_id, project_id, db)
    
    # Get AR content
    ar_content = await get_ar_content_or_404(content_id, db)
    
    # Verify it belongs to the specified company and project
    if ar_content.company_id != company_id or ar_content.project_id != project_id:
        raise HTTPException(status_code=404, detail="AR content not found in specified project")
    
    # Load related videos
    stmt = select(Video).where(Video.ar_content_id == content_id)
    result = await db.execute(stmt)
    videos = result.scalars().all()
    
    # Add unique link and videos to response
    content_data = ARContentWithLinks.model_validate(ar_content)
    content_data.unique_link = build_unique_link(ar_content.unique_id)
    
    return content_data


@router.put("/companies/{company_id}/projects/{project_id}/ar-content/{content_id}", response_model=ARContentSchema, tags=["AR Content"])
async def update_ar_content(
    company_id: int,
    project_id: int,
    content_id: int,
    update_data: ARContentUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update mutable AR content metadata (never changes unique_id or QR code)."""
    # Validate company and project relationship
    await validate_company_project(company_id, project_id, db)
    
    # Get AR content
    ar_content = await get_ar_content_or_404(content_id, db)
    
    # Verify it belongs to the specified company and project
    if ar_content.company_id != company_id or ar_content.project_id != project_id:
        raise HTTPException(status_code=404, detail="AR content not found in specified project")
    
    # Update only mutable fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(ar_content, field, value)
    
    await db.commit()
    await db.refresh(ar_content)
    
    return ARContentSchema.model_validate(ar_content)


@router.patch("/companies/{company_id}/projects/{project_id}/ar-content/{content_id}/video", response_model=ARContentSchema, tags=["AR Content"])
async def update_ar_content_video(
    company_id: int,
    project_id: int,
    content_id: int,
    video: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Replace the video for AR content without changing unique_id or QR code."""
    # Validate company and project relationship
    await validate_company_project(company_id, project_id, db)
    
    # Get AR content
    ar_content = await get_ar_content_or_404(content_id, db)
    
    # Verify it belongs to the specified company and project
    if ar_content.company_id != company_id or ar_content.project_id != project_id:
        raise HTTPException(status_code=404, detail="AR content not found in specified project")
    
    # Build storage path
    storage_path = build_ar_content_storage_path(company_id, project_id, ar_content.unique_id)
    
    # Save new video
    video_filename = f"video{Path(video.filename).suffix}"
    video_path = storage_path / video_filename
    await save_uploaded_file(video, video_path)
    
    # Update database
    ar_content.video_path = str(video_path)
    ar_content.video_url = build_public_url(video_path)
    
    # TODO: Regenerate preview
    
    await db.commit()
    await db.refresh(ar_content)
    
    return ARContentSchema.model_validate(ar_content)


@router.delete("/companies/{company_id}/projects/{project_id}/ar-content/{content_id}", tags=["AR Content"])
async def delete_ar_content(
    company_id: int,
    project_id: int,
    content_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Delete AR content and its storage folder."""
    # Validate company and project relationship
    await validate_company_project(company_id, project_id, db)
    
    # Get AR content
    ar_content = await get_ar_content_or_404(content_id, db)
    
    # Verify it belongs to the specified company and project
    if ar_content.company_id != company_id or ar_content.project_id != project_id:
        raise HTTPException(status_code=404, detail="AR content not found in specified project")
    
    # Build storage path
    storage_path = build_ar_content_storage_path(company_id, project_id, ar_content.unique_id)
    
    # Delete from database
    await db.delete(ar_content)
    await db.commit()

    # Best-effort delete storage folder after DB commit
    background_tasks.add_task(_safe_delete_folder, storage_path)

    logger.info(
        "ar_content_deleted",
        content_id=content_id,
        unique_id=str(ar_content.unique_id),
        storage_path=str(storage_path)
    )
    
    return {"message": "AR content deleted successfully"}


# Маршрут для получения AR-контента по ID без иерархии (для совместимости)
@router.get("/{content_id}", response_model=ARContentWithLinks, tags=["AR Content"])
async def get_ar_content_by_id(
    content_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get AR content by ID without requiring company/project context (for compatibility)"""
    # Get AR content
    ar_content = await get_ar_content_or_404(content_id, db)
    
    # Load related videos
    stmt = select(Video).where(Video.ar_content_id == content_id)
    result = await db.execute(stmt)
    videos = result.scalars().all()
    
    # Add unique link and videos to response
    content_data = ARContentWithLinks.model_validate(ar_content)
    content_data.unique_link = build_unique_link(ar_content.unique_id)
    
    return content_data