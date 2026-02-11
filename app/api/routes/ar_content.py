"""
AR Content API routes with Company → Project → AR Content hierarchy.
"""
from uuid import uuid4, UUID
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query, BackgroundTasks, Request
import shutil
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
import structlog
import re
from datetime import datetime

from app.services.thumbnail_service import thumbnail_service

from app.core.config import settings
from app.core.database import get_db
from app.models.ar_content import ARContent
from app.models.project import Project
from app.models.company import Company
from app.models.video import Video
from app.schemas.ar_content import (
    ARContent as ARContentSchema,
    ARContentUpdate,
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

from fastapi.responses import HTMLResponse
import json

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


async def get_ar_content_or_404(content_id: int, db: AsyncSession, load_relations: bool = False) -> ARContent:
    """Get AR content by ID or raise 404.
    
    Args:
        content_id: The AR content ID
        db: Database session
        load_relations: If True, load company and project relationships
    """
    if load_relations:
        stmt = select(ARContent).options(
            selectinload(ARContent.company),
            selectinload(ARContent.project)
        ).where(ARContent.id == content_id)
        result = await db.execute(stmt)
        content = result.scalar_one_or_none()
    else:
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


@router.get("/ar-content", response_model=ARContentList, tags=["AR Content"])
async def list_all_ar_content(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=1000, description="Number of items per page"),
    db: AsyncSession = Depends(get_db)
):
    """List all AR content across all companies and projects."""
    # Calculate offset from page and page_size
    skip = (page - 1) * page_size
    
    # Count total items
    count_stmt = select(func.count(ARContent.id))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()
    
    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size  # Ceiling division
    
    # Get items with pagination, sorted by created_at DESC (newest first)
    stmt = select(ARContent).options(
        selectinload(ARContent.company), 
        selectinload(ARContent.project)
    ).order_by(ARContent.created_at.desc()).offset(skip).limit(page_size)
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    return ARContentList(
        items=[ARContentSchema.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/ar-content/", response_model=ARContentList, tags=["AR Content"])
async def list_all_ar_content_no_slash(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=1000, description="Number of items per page"),
    db: AsyncSession = Depends(get_db)
):
    """List all AR content across all companies and projects (route with trailing slash)."""
    # This is just a redirect to the main function
    return await list_all_ar_content(page=page, page_size=page_size, db=db)


@router.get("/companies/{company_id}/projects/{project_id}/ar-content", response_model=ARContentList, tags=["AR Content"])
async def list_ar_content(
    company_id: int,
    project_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=1000, description="Number of items per page"),
    db: AsyncSession = Depends(get_db)
):
    """List AR content for a specific project within a company."""
    # Validate company and project relationship
    await validate_company_project(company_id, project_id, db)
    
    # Calculate offset from page and page_size
    skip = (page - 1) * page_size
    
    # Count total items for this company and project
    count_stmt = select(func.count(ARContent.id)).where(
        ARContent.company_id == company_id,
        ARContent.project_id == project_id
    )
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()
    
    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size  # Ceiling division
    
    stmt = select(ARContent).where(
        ARContent.company_id == company_id,
        ARContent.project_id == project_id
    ).options(selectinload(ARContent.company), selectinload(ARContent.project)).offset(skip).limit(page_size)
    
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    return ARContentList(
        items=[ARContentSchema.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


# Внутренняя функция для создания AR-контента
async def _create_ar_content(
    company_id: int,
    project_id: int,
    customer_name: Optional[str],
    customer_phone: Optional[str],
    customer_email: Optional[str],
    duration_years: int,
    photo_file: UploadFile,
    video_file: UploadFile,
    auto_enhance: bool,
    db: AsyncSession
):
    """Внутренняя функция для создания AR-контента"""
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
    
    # Note: file size validation (e.g. 10MB photo, 100MB video) can be added here if needed

    # Generate unique identifier
    unique_id = str(uuid4())
    
    # Generate order number
    order_number = generate_order_number()
    
    # Build storage path with company and project names
    storage_path = build_ar_content_storage_path(
        company_id=company_id,
        project_id=project_id,
        order_number=order_number,
        company_name=company.name,
        project_name=project.name
    )
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
    logger.info(
        "ar_content_storage_paths",
        storage_path=str(storage_path),
        photo_path=str(photo_path),
        video_path=str(video_path),
        qr_code_path=str(storage_path / "qr_code.png"),
        photo_url=build_public_url(photo_path),
        video_url=video_url,
        qr_code_url=qr_code_url,
    )

    # Analyze photo quality and build recommendations
    image_quality = marker_service.analyze_image_quality(str(photo_path))
    recommendations = marker_service.build_image_recommendations(image_quality)
    photo_analysis: dict = {
        "metrics": image_quality,
        "recommendations": recommendations,
        "auto_enhanced": False,
    }

    marker_image_path = str(photo_path)
    if auto_enhance:
        if marker_service.should_auto_enhance(image_quality):
            enhanced_photo_path = storage_path / "photo_enhanced.png"
            enhanced_path = marker_service.enhance_image_for_marker(
                image_path=str(photo_path),
                output_path=str(enhanced_photo_path),
            )
            if enhanced_path:
                marker_image_path = enhanced_path
                enhanced_metrics = marker_service.analyze_image_quality(enhanced_path)
                photo_analysis.update(
                    {
                        "auto_enhanced": True,
                        "enhanced_metrics": enhanced_metrics,
                    }
                )
        else:
            photo_analysis["auto_enhance_skipped_reason"] = "quality_above_threshold"
    
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
    
    # Add to session before processing
    db.add(ar_content)
    await db.commit()
    await db.refresh(ar_content)
    
    # Generate thumbnail (use enhanced image path when auto-enhance was applied)
    try:
        thumbnail_result = await thumbnail_service.generate_image_thumbnail(
            image_path=marker_image_path,
            company_id=company_id,
            storage_path=storage_path
        )
        
        if thumbnail_result.get("status") == "ready":
            # Update the AR content with thumbnail URL
            ar_content.thumbnail_url = thumbnail_result.get("thumbnail_url")
            # Commit the change to the database
            await db.commit()
            await db.refresh(ar_content)  # Refresh to ensure the change is saved
            logger.info(
                "photo_thumbnail_generation_saved",
                ar_content_id=ar_content.id,
                thumbnail_url=thumbnail_result.get("thumbnail_url"),
                thumbnail_path=thumbnail_result.get("thumbnail_path"),
            )
        else:
            logger.warning("photo_thumbnail_generation_failed", error=thumbnail_result.get("error"))
            # We won't fail the whole request if thumbnail generation fails
    except Exception as e:
        logger.error("photo_thumbnail_generation_exception", error=str(e))
        # We won't fail the whole request if thumbnail generation fails
    
    # Create video record
    video_record = Video(
        ar_content_id=ar_content.id,
        filename=video_filename,
        video_path=str(video_path),
        video_url=video_url,
        preview_url=video_url,  # Use the same URL as video_url for preview
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
    
    # ARCore: marker = photo image (no .mind generation)
    try:
        ar_content.marker_path = str(photo_path)
        ar_content.marker_url = build_public_url(photo_path)
        ar_content.marker_status = "ready"
        ar_content.marker_metadata = {}
        ar_content.status = "ready"
        await db.commit()
        await db.refresh(ar_content)
        logger.info(
            "marker_saved_from_photo",
            ar_content_id=ar_content.id,
            marker_url=ar_content.marker_url,
            marker_status=ar_content.marker_status,
        )
        # Create notification for successful AR content creation
        try:
            from app.services.notification_service import create_notification

            stmt = select(ARContent).options(
                selectinload(ARContent.company),
                selectinload(ARContent.project)
            ).where(ARContent.id == ar_content.id)
            result = await db.execute(stmt)
            ar_content_loaded = result.scalar_one()
            company_name = ar_content_loaded.company.name if ar_content_loaded.company else None
            project_name = ar_content_loaded.project.name if ar_content_loaded.project else None
            await create_notification(
                db=db,
                notification_type="ar_content_created",
                subject=f"New AR Content Created: {ar_content.order_number}",
                message=f"AR content '{ar_content.order_number}' has been successfully created and is ready for use.",
                company_id=company_id,
                project_id=project_id,
                ar_content_id=ar_content.id,
                metadata={
                    "is_read": False,
                    "company_name": company_name,
                    "project_name": project_name,
                    "ar_content_name": ar_content.order_number
                }
            )
        except Exception as e:
            logger.warning("failed_to_create_notification", error=str(e))
    except Exception as e:
        logger.error("marker_save_exception", error=str(e))
    
    return ARContentCreateResponse(
        id=ar_content.id,
        order_number=ar_content.order_number,
        public_link=build_unique_link(ar_content.unique_id),
        qr_code_url=ar_content.qr_code_url,
        photo_url=ar_content.photo_url,
        video_url=ar_content.video_url,
        photo_analysis=photo_analysis,
    )


@router.post("/ar-content/{ar_content_id}/regenerate-media", tags=["AR Content"])
async def regenerate_media(
    ar_content_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Regenerate preview thumbnail and marker for AR content."""
    try:
        ar_content = await db.get(ARContent, ar_content_id)
        if not ar_content:
            logger.error("ar_content_not_found", ar_content_id=ar_content_id)
            raise HTTPException(status_code=404, detail="AR content not found")

        if not ar_content.photo_path:
            logger.error("photo_not_found", ar_content_id=ar_content_id)
            raise HTTPException(status_code=400, detail="Photo not found for AR content")

        logger.info(
            "ar_content_regeneration_started",
            ar_content_id=ar_content.id,
            photo_path=ar_content.photo_path,
        )

        # Get storage path for thumbnail
        from app.utils.ar_content import get_ar_content_storage_path
        try:
            storage_path = await get_ar_content_storage_path(ar_content, db)
            logger.info("storage_path_resolved", storage_path=str(storage_path))
        except Exception as e:
            logger.error("storage_path_resolution_failed", error=str(e), ar_content_id=ar_content.id)
            # Try to use photo_path parent as fallback
            if ar_content.photo_path:
                storage_path = Path(ar_content.photo_path).parent
            else:
                raise HTTPException(status_code=500, detail="Could not determine storage path")
        
        # Generate thumbnail
        try:
            thumbnail_result = await thumbnail_service.generate_image_thumbnail(
                image_path=ar_content.photo_path,
                storage_path=storage_path,
                company_id=ar_content.company_id
            )
            if thumbnail_result.get("status") == "ready":
                ar_content.thumbnail_url = thumbnail_result.get("thumbnail_url")
                logger.info("thumbnail_generated", thumbnail_url=ar_content.thumbnail_url)
            else:
                logger.warning(
                    "photo_thumbnail_regeneration_failed",
                    ar_content_id=ar_content.id,
                    error=thumbnail_result.get("error"),
                )
        except Exception as e:
            logger.error("thumbnail_generation_exception", error=str(e), ar_content_id=ar_content.id, exc_info=True)

        # ARCore: marker = photo image (no .mind generation)
        try:
            photo_path_obj = Path(ar_content.photo_path)
            ar_content.marker_path = ar_content.photo_path
            ar_content.marker_url = build_public_url(photo_path_obj)
            ar_content.marker_status = "ready"
            ar_content.marker_metadata = {}
            logger.info("marker_saved_from_photo", marker_url=ar_content.marker_url, ar_content_id=ar_content.id)
        except Exception as e:
            logger.error("marker_save_exception", error=str(e), ar_content_id=ar_content.id, exc_info=True)

        await db.commit()
        await db.refresh(ar_content)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("regenerate_media_exception", error=str(e), ar_content_id=ar_content_id, exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to regenerate media: {str(e)}")

    logger.info(
        "ar_content_regeneration_completed",
        ar_content_id=ar_content.id,
        thumbnail_url=ar_content.thumbnail_url,
        marker_url=ar_content.marker_url,
        marker_status=ar_content.marker_status,
    )

    # Return success response
    return {
        "status": "completed",
        "thumbnail_url": ar_content.thumbnail_url,
        "marker_url": ar_content.marker_url,
        "marker_status": ar_content.marker_status,
        "marker_metadata": ar_content.marker_metadata
    }


@router.post("/ar-content", response_model=ARContentCreateResponse, tags=["AR Content"])
async def create_ar_content(
    company_id: int = Form(...),
    project_id: int = Form(...),
    customer_name: Optional[str] = Form(None),
    customer_phone: Optional[str] = Form(None),
    customer_email: Optional[str] = Form(None),
    duration_years: int = Form(...),
    auto_enhance: bool = Form(False),
    photo_file: UploadFile = File(...),
    video_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Create new AR content with photo and video files."""
    return await _create_ar_content(
        company_id=company_id,
        project_id=project_id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_email=customer_email,
        duration_years=duration_years,
        photo_file=photo_file,
        video_file=video_file,
        auto_enhance=auto_enhance,
        db=db
    )


async def parse_ar_content_data(request: Request):
    """
    Custom dependency to parse AR content data from request that can handle both formats:
    - New format: photo_file, video_file, customer_name, etc.
    - Legacy format: image, video, content_metadata (JSON string)
    """
    # Get form data
    form = await request.form()

    def _parse_bool(value: Optional[str]) -> bool:
        if value is None:
            return False
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    auto_enhance = _parse_bool(form.get("auto_enhance"))

    # Check if it's the legacy format (with content_metadata)
    if "content_metadata" in form:
        # Legacy format
        content_metadata_str = form.get("content_metadata")
        
        # Parse the content metadata JSON string
        import json
        try:
            metadata = json.loads(content_metadata_str)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid content_metadata JSON format")
        
        # Extract fields from metadata
        customer_name = metadata.get("customer_name")
        customer_phone = metadata.get("customer_phone")
        customer_email = metadata.get("customer_email")
        
        # Map playback_duration to duration_years
        playback_duration = metadata.get("playback_duration", "1_year")
        duration_mapping = {
            "1_year": 1,
            "3_years": 3,
            "5_years": 5
        }
        duration_years = duration_mapping.get(playback_duration, 1)
        
        # Get files (image/video for legacy, photo_file/video_file for new)
        image_file = form.get("image")
        video_file = form.get("video")
        photo_file = form.get("photo_file")
        video_file_param = form.get("video_file")
        
        # Use image/video if photo_file/video_file not provided
        actual_photo_file = photo_file or image_file
        actual_video_file = video_file_param or video_file
        
        if not actual_photo_file or not actual_video_file:
            raise HTTPException(status_code=400, detail="Both photo and video files are required")
    
    else:
        # New format
        customer_name = form.get("customer_name")
        customer_phone = form.get("customer_phone")
        customer_email = form.get("customer_email")
        
        # Parse duration_years
        duration_years_str = form.get("duration_years")
        if not duration_years_str:
            raise HTTPException(status_code=400, detail="duration_years is required")
        
        try:
            duration_years = int(duration_years_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="duration_years must be an integer")
        
        # Get files
        actual_photo_file = form.get("photo_file")
        actual_video_file = form.get("video_file")
        
        if not actual_photo_file or not actual_video_file:
            raise HTTPException(status_code=400, detail="Both photo_file and video_file are required")
    
    return {
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "customer_email": customer_email,
        "duration_years": duration_years,
        "photo_file": actual_photo_file,
        "video_file": actual_video_file,
        "auto_enhance": auto_enhance,
    }


@router.post("/companies/{company_id}/projects/{project_id}/ar-content", response_model=ARContentCreateResponse, tags=["AR Content"])
async def create_ar_content_hierarchical(
    company_id: int,
    project_id: int,
    data: dict = Depends(parse_ar_content_data),
    db: AsyncSession = Depends(get_db)
):
    """Create new AR content within a specific company and project with photo and video files."""
    log = structlog.get_logger()
    log.info(
        "ar_content_creation_request",
        company_id=company_id,
        project_id=project_id,
        customer_name=data.get("customer_name"),
        customer_phone=data.get("customer_phone"),
        customer_email=data.get("customer_email"),
        duration_years=data.get("duration_years"),
        auto_enhance=data.get("auto_enhance"),
        photo_filename=data["photo_file"].filename if data.get("photo_file") else None,
        video_filename=data["video_file"].filename if data.get("video_file") else None,
    )
    try:
        return await _create_ar_content(
            company_id=company_id,
            project_id=project_id,
            customer_name=data.get("customer_name"),
            customer_phone=data.get("customer_phone"),
            customer_email=data.get("customer_email"),
            duration_years=data["duration_years"],
            photo_file=data["photo_file"],
            video_file=data["video_file"],
            auto_enhance=bool(data.get("auto_enhance")),
            db=db
        )
    except HTTPException:
        raise
    except Exception as e:
        log.error(
            "ar_content_creation_failed",
            company_id=company_id,
            project_id=project_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Не удалось создать AR контент: {str(e)}",
        )


@router.post("/companies/{company_id}/projects/{project_id}/ar-content-legacy", response_model=ARContentCreateResponse, tags=["AR Content"])
async def create_ar_content_legacy(
    company_id: int,
    project_id: int,
    content_metadata: str = Form(...),
    image: UploadFile = File(...),
    video: UploadFile = File(...),
    description: str = Form(""),
    db: AsyncSession = Depends(get_db)
):
    """Create new AR content with legacy format (image/video files and JSON metadata string)."""
    logger = structlog.get_logger()

    # Parse the content metadata JSON string
    try:
        metadata = json.loads(content_metadata)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid content_metadata JSON format")
    
    # Extract fields from metadata
    customer_name = metadata.get("customer_name")
    customer_phone = metadata.get("customer_phone")
    customer_email = metadata.get("customer_email")
    
    # Map playback_duration to duration_years
    playback_duration = metadata.get("playback_duration", "1_year")
    duration_mapping = {
        "1_year": 1,
        "3_years": 3,
        "5_years": 5
    }
    duration_years = duration_mapping.get(playback_duration, 1)
    
    logger.info(
        "ar_content_creation_legacy_request",
        company_id=company_id,
        project_id=project_id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_email=customer_email,
        duration_years=duration_years,
        image_filename=image.filename if image else None,
        video_filename=video.filename if video else None,
        metadata=metadata
    )
    
    # Call the internal function with the extracted values
    return await _create_ar_content(
        company_id=company_id,
        project_id=project_id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_email=customer_email,
        duration_years=duration_years,
        photo_file=image,  # Map 'image' to 'photo_file'
        video_file=video,  # Map 'video' to 'video_file'
        auto_enhance=False,
        db=db
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
    
    # Get AR content with related videos, company, and project
    stmt = select(ARContent).options(
        selectinload(ARContent.videos),
        selectinload(ARContent.active_video),
        selectinload(ARContent.company),
        selectinload(ARContent.project)
    ).where(ARContent.id == content_id)
    result = await db.execute(stmt)
    ar_content = result.scalar()
    
    # Verify it belongs to the specified company and project
    if ar_content.company_id != company_id or ar_content.project_id != project_id:
        raise HTTPException(status_code=404, detail="AR content not found in specified project")
    
    # Add unique link and videos to response
    content_data = ARContentWithLinks.model_validate(ar_content)
    # Set unique_link after validation since it's not in the database model
    content_data.unique_link = build_unique_link(ar_content.unique_id)
    # Set public_url as alias for unique_link
    content_data.public_url = content_data.unique_link
    # Set company and project IDs
    content_data.company_id = ar_content.company_id
    content_data.project_id = ar_content.project_id
    # Set storage path
    from app.utils.ar_content import build_ar_content_storage_path
    storage_path = build_ar_content_storage_path(
        company_id=ar_content.company_id,
        project_id=ar_content.project_id,
        order_number=ar_content.order_number,
        company_name=ar_content.company.name if ar_content.company else None,
        project_name=ar_content.project.name if ar_content.project else None
    )
    content_data.storage_path = str(storage_path)
    # Set company and project names
    if ar_content.company:
        content_data.company_name = ar_content.company.name
    if ar_content.project:
        content_data.project_name = ar_content.project.name
    
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


@router.patch("/companies/{company_id}/projects/{project_id}/ar-content/{content_id}/photo", response_model=ARContentSchema, tags=["AR Content"])
async def update_ar_content_photo(
    company_id: int,
    project_id: int,
    content_id: int,
    photo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Replace the photo for AR content and re-generate dependent assets (thumbnail, marker)."""
    # Validate company and project relationship
    await validate_company_project(company_id, project_id, db)

    # Get AR content with relations
    ar_content = await get_ar_content_or_404(content_id, db, load_relations=True)

    # Verify it belongs to the specified company and project
    if ar_content.company_id != company_id or ar_content.project_id != project_id:
        raise HTTPException(status_code=404, detail="AR content not found in specified project")

    # Get storage path
    from app.utils.ar_content import get_ar_content_storage_path
    storage_path = await get_ar_content_storage_path(ar_content, db)
    storage_path.mkdir(parents=True, exist_ok=True)

    # Save new photo
    photo_filename = f"photo{Path(photo.filename).suffix}"
    photo_path = storage_path / photo_filename
    await save_uploaded_file(photo, photo_path)

    # Update database
    ar_content.photo_path = str(photo_path)
    ar_content.photo_url = build_public_url(photo_path)

    # (Best-effort) regenerate thumbnail
    try:
        thumbnail_result = await thumbnail_service.generate_image_thumbnail(
            image_path=str(photo_path),
            storage_path=storage_path,
            company_id=company_id,
        )
        if thumbnail_result.get("status") == "ready":
            ar_content.thumbnail_url = thumbnail_result.get("thumbnail_url")
        else:
            logger.warning("photo_thumbnail_generation_failed", error=thumbnail_result.get("error"))
    except Exception as e:
        logger.error("photo_thumbnail_generation_exception", error=str(e))

    # ARCore: marker = photo image (no .mind generation)
    try:
        ar_content.marker_path = str(photo_path)
        ar_content.marker_url = build_public_url(photo_path)
        ar_content.marker_status = "ready"
        ar_content.marker_metadata = {}
        ar_content.status = "ready"
    except Exception as e:
        logger.error("marker_save_exception", error=str(e))

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
    
    # Get AR content with relations
    ar_content = await get_ar_content_or_404(content_id, db, load_relations=True)
    
    # Verify it belongs to the specified company and project
    if ar_content.company_id != company_id or ar_content.project_id != project_id:
        raise HTTPException(status_code=404, detail="AR content not found in specified project")
    
    # Get storage path
    from app.utils.ar_content import get_ar_content_storage_path
    storage_path = await get_ar_content_storage_path(ar_content, db)
    storage_path.mkdir(parents=True, exist_ok=True)
    
    # Save new video
    video_filename = f"video{Path(video.filename).suffix}"
    video_path = storage_path / video_filename
    await save_uploaded_file(video, video_path)
    
    # Update database
    ar_content.video_path = str(video_path)
    ar_content.video_url = build_public_url(video_path)
    # Update preview URL as well
    if ar_content.active_video:
        ar_content.active_video.preview_url = build_public_url(video_path)
    
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
    
    # Get AR content with relations
    ar_content = await get_ar_content_or_404(content_id, db, load_relations=True)
    
    # Verify it belongs to the specified company and project
    if ar_content.company_id != company_id or ar_content.project_id != project_id:
        raise HTTPException(status_code=404, detail="AR content not found in specified project")
    
    # Get storage path
    from app.utils.ar_content import get_ar_content_storage_path
    storage_path = await get_ar_content_storage_path(ar_content, db)
    
    # Clear the active_video_id reference to avoid circular dependency
    ar_content.active_video_id = None
    await db.commit()
    
    # Delete from database (this will cascade delete related videos due to cascade="all, delete-orphan")
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


@router.get("/ar-content/{content_id}", response_model=ARContentWithLinks, tags=["AR Content"])
async def get_ar_content_by_id(
    content_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get AR content by ID without requiring company/project context"""
    # Get AR content with related videos, company, and project
    stmt = select(ARContent).options(
        selectinload(ARContent.videos),
        selectinload(ARContent.active_video),
        selectinload(ARContent.company),
        selectinload(ARContent.project)
    ).where(ARContent.id == content_id)
    result = await db.execute(stmt)
    ar_content = result.scalar()
    
    if not ar_content:
        raise HTTPException(status_code=404, detail="AR content not found")

    # Ensure unique_id exists (legacy records may lack it)
    uid = (ar_content.unique_id or "").strip()
    if not uid:
        uid = str(uuid4())
        ar_content.unique_id = uid
        await db.commit()

    # Add unique_id, unique_link and full public URL to response
    content_data = ARContentWithLinks.model_validate(ar_content)
    content_data.unique_id = uid
    content_data.unique_link = build_unique_link(uid)
    base = (settings.PUBLIC_URL or "").rstrip("/")
    content_data.public_url = f"{base}{content_data.unique_link}" if base else content_data.unique_link
    # Set company and project IDs
    content_data.company_id = ar_content.company_id
    content_data.project_id = ar_content.project_id
    # Set storage path
    from app.utils.ar_content import build_ar_content_storage_path
    storage_path = build_ar_content_storage_path(
        company_id=ar_content.company_id,
        project_id=ar_content.project_id,
        order_number=ar_content.order_number,
        company_name=ar_content.company.name if ar_content.company else None,
        project_name=ar_content.project.name if ar_content.project else None
    )
    content_data.storage_path = str(storage_path)
    # Set company and project names
    if ar_content.company:
        content_data.company_name = ar_content.company.name
    if ar_content.project:
        content_data.project_name = ar_content.project.name
    
    return content_data


@router.delete("/ar-content/{content_id}", tags=["AR Content"])
async def delete_ar_content_by_id(
    content_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Delete AR content by ID without requiring company/project context"""
    # Get AR content with relations for building proper storage path
    ar_content = await get_ar_content_or_404(content_id, db, load_relations=True)
    
    # Get storage path
    from app.utils.ar_content import get_ar_content_storage_path
    storage_path = await get_ar_content_storage_path(ar_content, db)
    
    # Clear the active_video_id reference to avoid circular dependency
    ar_content.active_video_id = None
    await db.commit()
    
    # Delete from database (this will cascade delete related videos due to cascade="all, delete-orphan")
    # Use await for async delete operation
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


@router.get("/{content_id}", response_model=ARContentWithLinks, tags=["AR Content"])
async def get_ar_content_by_id_legacy(
    content_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get AR content by ID without requiring company/project context"""
    # Get AR content
    ar_content = await get_ar_content_or_404(content_id, db)

    # Add unique link to response
    content_data = ARContentWithLinks.model_validate(ar_content)
    # Set unique_link after validation since it's not in the database model
    content_data.unique_link = build_unique_link(ar_content.unique_id)
    
    return content_data


# AR viewer landing page (AR in app only; MindAR removed)
@router.get("/view/{unique_id}", response_class=HTMLResponse, tags=["AR Content"])
async def get_ar_viewer(
    request: Request,
    unique_id: str,
    diagnose: Optional[str] = Query(None, description="Включить диагностику AR (отправка таймингов): ?diagnose=1"),
    db: AsyncSession = Depends(get_db),
):
    """Landing page: open in AR Viewer app or download from Play Store. AR is no longer in browser."""
    logger.info("ar_viewer_landing_request", unique_id=unique_id)
    try:
        UUID(unique_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid unique_id format")
    try:
        stmt = select(ARContent).where(ARContent.unique_id == unique_id)
        result = await db.execute(stmt)
        ar_content = result.scalar_one_or_none()
        if not ar_content:
            raise HTTPException(status_code=404, detail="AR content not found")
        from datetime import datetime, timedelta, timezone
        creation_date = ar_content.created_at.replace(tzinfo=None) if ar_content.created_at.tzinfo else ar_content.created_at
        expiry_date = creation_date + timedelta(days=ar_content.duration_years * 365)
        current_date = datetime.now(timezone.utc).replace(tzinfo=None)
        if current_date > expiry_date:
            raise HTTPException(status_code=403, detail="AR content subscription has expired")
        if ar_content.status not in ["active", "ready"]:
            raise HTTPException(status_code=400, detail="AR content is not active or ready")
        photo_ok = bool(ar_content.photo_url or ar_content.photo_path)
        if not photo_ok:
            raise HTTPException(status_code=400, detail="Photo (marker image) not available")
        base_url = (settings.PUBLIC_URL or "").rstrip("/")
        app_link = f"{base_url}/view/{unique_id}" if base_url else f"/view/{unique_id}"
        deep_link = "arv://view/" + unique_id
        logger.info(
            "ar_viewer_landing_ok",
            unique_id=unique_id,
            ar_content_id=ar_content.id,
            app_link=app_link,
        )
        play_store_url = "https://play.google.com/store/apps/details?id=ru.neuroimagen.arviewer"
        import html as html_escape
        order_esc = html_escape.escape(ar_content.order_number or "AR")
        html_content = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AR Viewer — {order_esc}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #1a1a1a; color: #eee; min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 20px; }}
        h1 {{ font-size: 1.5rem; margin-bottom: 0.5rem; }}
        p {{ font-size: 0.95rem; opacity: 0.9; margin-bottom: 1.5rem; text-align: center; max-width: 320px; }}
        a {{ display: inline-block; margin: 8px; padding: 14px 24px; border-radius: 8px; font-size: 1rem; text-decoration: none; font-weight: 500; }}
        .btn-app {{ background: #1a73e8; color: white; }}
        .btn-store {{ background: #0d652d; color: white; }}
        .btn-browser {{ background: rgba(255,255,255,0.12); color: #ccc; border: 1px solid rgba(255,255,255,0.2); }}
    </style>
</head>
<body>
    <h1>AR Viewer</h1>
    <p>Просмотр AR доступен в приложении. Откройте ссылку в приложении или установите его из Google Play.</p>
    <a class="btn-app" href="{html_escape.escape(deep_link)}">Открыть в приложении</a>
    <a class="btn-app" href="{html_escape.escape(app_link)}">Открыть по ссылке</a>
    <a class="btn-store" href="{html_escape.escape(play_store_url)}">Скачать в Google Play</a>
    <a class="btn-browser" href="#">Открыть в браузере</a>
    <p style="margin-top: 1.5rem; font-size: 0.85rem; opacity: 0.6;">AR-контент отображается только в приложении AR Viewer (Android, ARCore).</p>
</body>
</html>"""
        return HTMLResponse(content=html_content)
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid unique_id format")
    except Exception as e:
        logger.error("ar_viewer_error", unique_id=unique_id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/ar-content/{ar_content_id}/marker/validate", tags=["AR Content"])
async def validate_marker(
    ar_content_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Validate AR marker (photo image) availability and basic quality for ARCore.
    No .mind file validation; marker = photo image.
    """
    try:
        ar_content = await db.get(ARContent, ar_content_id)
        if not ar_content:
            raise HTTPException(status_code=404, detail="AR content not found")
        image_path = ar_content.marker_path or ar_content.photo_path
        if not image_path:
            raise HTTPException(
                status_code=400,
                detail="Marker (photo) not set. Please upload photo or regenerate media."
            )
        path = Path(image_path)
        if not path.is_absolute():
            path = Path(settings.STORAGE_BASE_PATH) / image_path
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"Marker image not found at {image_path}")
        width = height = image_size = None
        try:
            import cv2
            img = cv2.imread(str(path))
            if img is not None:
                height, width = img.shape[:2]
                image_size = width * height
        except Exception:
            pass
        quality_assessment = "good" if (width and height and width >= 100 and height >= 100) else "fair"
        recommendations = ["ARCore uses the photo as the tracking image. Use a clear, well-lit image for best results."]
        if width and height and (width < 320 or height < 320):
            recommendations.append("Higher resolution (e.g. 640x480 or more) may improve tracking.")
        logger.info("marker_validation_requested", ar_content_id=ar_content_id, width=width, height=height)
        return {
            "ar_content_id": ar_content_id,
            "order_number": ar_content.order_number,
            "marker_url": ar_content.marker_url,
            "marker_path": ar_content.marker_path,
            "validation": {
                "is_valid": True,
                "width": width,
                "height": height,
                "image_size": image_size,
                "quality_assessment": quality_assessment,
                "warnings": [],
            },
            "metadata": ar_content.marker_metadata or {},
            "recommendations": recommendations,
            "status": "ready",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("marker_validation_error", error=str(e), ar_content_id=ar_content_id, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to validate marker: {str(e)}")


# Endpoint to get marker file by unique_id
@router.get("/ar-content/marker/{unique_id}", tags=["AR Content"])
async def get_ar_marker(unique_id: str, db: AsyncSession = Depends(get_db)):
    """Get AR marker file by unique_id"""
    try:
        # Validate UUID format
        UUID(unique_id)

        # Find AR content by unique_id (using string directly since model expects string)
        stmt = select(ARContent).where(ARContent.unique_id == unique_id)
        result = await db.execute(stmt)
        ar_content = result.scalar()
        
        if not ar_content:
            raise HTTPException(status_code=404, detail="AR content not found")
        
        if not ar_content.marker_url:
            raise HTTPException(status_code=404, detail="AR marker not available")
            
        # Return a redirect to the marker URL or serve the file directly
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=ar_content.marker_url)
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid unique_id format")


# Endpoint to get image by unique_id
@router.get("/ar-content/image/{unique_id}", tags=["AR Content"])
async def get_ar_image(unique_id: str, db: AsyncSession = Depends(get_db)):
    """Get AR target image by unique_id"""
    try:
        # Validate UUID format
        UUID(unique_id)

        # Find AR content by unique_id (using string directly since model expects string)
        stmt = select(ARContent).where(ARContent.unique_id == unique_id)
        result = await db.execute(stmt)
        ar_content = result.scalar()
        
        if not ar_content:
            raise HTTPException(status_code=404, detail="AR content not found")
        
        if not ar_content.photo_url:
            raise HTTPException(status_code=404, detail="AR target image not available")
            
        # Return a redirect to the image URL or serve the file directly
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=ar_content.photo_url)
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid unique_id format")