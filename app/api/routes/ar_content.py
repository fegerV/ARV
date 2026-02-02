"""
AR Content API routes with Company → Project → AR Content hierarchy.
"""
from app.middleware.rate_limiter import rate_limit
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

# Add import for the viewer route
from fastapi.staticfiles import StaticFiles
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
    
    # Validate file sizes
    MAX_FILE_SIZE_PHOTO = 10 * 1024 * 1024  # 10MB
    MAX_FILE_SIZE_VIDEO = 100 * 1024 * 1024  # 100MB
    
    # Note: In a real implementation, we'd need to check the actual file size
    # For now, we'll assume the files are within limits
    
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
    
    # Generate thumbnail for the photo
    try:
        thumbnail_result = await thumbnail_service.generate_image_thumbnail(
            image_path=str(photo_path),
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
    
    # Generate Mind AR marker
    try:
        marker_result = await marker_service.generate_marker(
            ar_content_id=ar_content.id,
            image_path=marker_image_path,
            storage_path=storage_path
        )
        
        # Update AR content with marker information
        ar_content.marker_path = marker_result.get("marker_path")
        ar_content.marker_url = marker_result.get("marker_url")
        ar_content.marker_status = marker_result.get("status")
        ar_content.marker_metadata = marker_result.get("metadata")
        
        if marker_result.get("status") == "failed":
            logger.error("marker_generation_failed", error=marker_result.get("error"))
            # Keep status as "pending" if marker generation failed
        else:
            # Update status to "ready" after successful marker generation
            ar_content.status = "ready"
            # Commit the marker information to database
            await db.commit()
            await db.refresh(ar_content)
            logger.info(
                "marker_generation_saved",
                ar_content_id=ar_content.id,
                marker_url=marker_result.get("marker_url"),
                marker_path=marker_result.get("marker_path"),
                marker_status=marker_result.get("status"),
                status="ready"
            )
            
            # Create notification for successful AR content creation
            try:
                from app.services.notification_service import create_notification
                
                # Load company and project names for notification
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
        logger.error("marker_generation_exception", error=str(e))
        # We won't fail the whole request if marker generation fails
    
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

        # Generate marker
        try:
            marker_result = await marker_service.generate_marker(
                ar_content_id=ar_content.id,
                image_path=ar_content.photo_path,
                storage_path=storage_path
            )
            ar_content.marker_path = marker_result.get("marker_path")
            ar_content.marker_url = marker_result.get("marker_url")
            ar_content.marker_status = marker_result.get("status")
            ar_content.marker_metadata = marker_result.get("metadata")

            if marker_result.get("status") == "failed":
                logger.error("marker_regeneration_failed", error=marker_result.get("error"), ar_content_id=ar_content.id)
            else:
                logger.info("marker_generated", marker_url=ar_content.marker_url, marker_status=ar_content.marker_status)
        except Exception as e:
            logger.error("marker_generation_exception", error=str(e), ar_content_id=ar_content.id, exc_info=True)

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


from fastapi import Request

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
    logger = structlog.get_logger()
    
    logger.info(
        "ar_content_creation_request",
        company_id=company_id,
        project_id=project_id,
        customer_name=data["customer_name"],
        customer_phone=data["customer_phone"],
        customer_email=data["customer_email"],
        duration_years=data["duration_years"],
        auto_enhance=data.get("auto_enhance"),
        photo_filename=data["photo_file"].filename if data["photo_file"] else None,
        video_filename=data["video_file"].filename if data["video_file"] else None
    )
    
    return await _create_ar_content(
        company_id=company_id,
        project_id=project_id,
        customer_name=data["customer_name"],
        customer_phone=data["customer_phone"],
        customer_email=data["customer_email"],
        duration_years=data["duration_years"],
        photo_file=data["photo_file"],
        video_file=data["video_file"],
        auto_enhance=bool(data.get("auto_enhance")),
        db=db
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
    import json
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
            company_id=company_id,
        )
        if thumbnail_result.get("status") == "ready":
            ar_content.thumbnail_url = thumbnail_result.get("thumbnail_url")
        else:
            logger.warning("photo_thumbnail_generation_failed", error=thumbnail_result.get("error"))
    except Exception as e:
        logger.error("photo_thumbnail_generation_exception", error=str(e))

    # (Best-effort) regenerate MindAR marker
    try:
        marker_result = await marker_service.generate_marker(
            ar_content_id=ar_content.id,
            image_path=str(photo_path),
            storage_path=storage_path
        )

        ar_content.marker_path = marker_result.get("marker_path")
        ar_content.marker_url = marker_result.get("marker_url")
        ar_content.marker_status = marker_result.get("status")
        ar_content.marker_metadata = marker_result.get("metadata")

        if marker_result.get("status") == "failed":
            logger.error("marker_generation_failed", error=marker_result.get("error"))
        else:
            # Update status to "ready" after successful marker generation
            ar_content.status = "ready"
    except Exception as e:
        logger.error("marker_generation_exception", error=str(e))

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
    
    # Load related videos
    stmt = select(Video).where(Video.ar_content_id == content_id)
    result = await db.execute(stmt)
    videos = result.scalars().all()
    
    # Add unique link to response
    content_data = ARContentWithLinks.model_validate(ar_content)
    # Set unique_link after validation since it's not in the database model
    content_data.unique_link = build_unique_link(ar_content.unique_id)
    
    return content_data


# AR viewer endpoint
@router.get("/view/{unique_id}", response_class=HTMLResponse, tags=["AR Content"])
async def get_ar_viewer(
    request: Request,
    unique_id: str,
    diagnose: Optional[str] = Query(None, description="Включить диагностику AR (отправка таймингов): ?diagnose=1"),
    db: AsyncSession = Depends(get_db),
):
    """Get AR viewer page for a specific AR content. Use ?diagnose=1 to enable diagnostic timing."""
    # On mobile, load MindAR only from our server (no CDN) to avoid timeouts/blocks
    ua = (request.headers.get("user-agent") or "")
    is_mobile_request = bool(re.search(r"(?i)Mobile|Android|iP(hone|od)", ua))
    logger.info("ar_viewer_request", unique_id=unique_id, user_agent=ua[:100], is_mobile=is_mobile_request)
    try:
        # Validate UUID format
        parsed_uuid = UUID(unique_id)
        
        # Find AR content by unique_id (using string directly since model expects string)
        stmt = select(ARContent).where(ARContent.unique_id == unique_id)
        result = await db.execute(stmt)
        ar_content = result.scalar()
        
        if not ar_content:
            raise HTTPException(status_code=404, detail="AR content not found")
        
        # Check if content has expired based on duration_years
        from datetime import datetime, timedelta, timezone
        creation_date = ar_content.created_at.replace(tzinfo=None) if ar_content.created_at.tzinfo else ar_content.created_at
        expiry_date = creation_date + timedelta(days=ar_content.duration_years * 365)
        current_date = datetime.now(timezone.utc).replace(tzinfo=None)
        
        if current_date > expiry_date:
            raise HTTPException(status_code=403, detail="AR content subscription has expired")
        
        # Check if marker is available
        if not ar_content.marker_url:
            if ar_content.marker_status == "pending":
                raise HTTPException(status_code=400, detail="AR marker is being generated, please try again later")
            else:
                raise HTTPException(status_code=400, detail="AR marker not available")
        
        # Recalculate URLs from paths to ensure they are correct
        from app.utils.ar_content import build_public_url
        from pathlib import Path
        from app.core.config import settings
        
        # Recalculate marker URL
        marker_url = ar_content.marker_url
        if ar_content.marker_path:
            try:
                marker_path = Path(ar_content.marker_path)
                if marker_path.is_absolute():
                    marker_url = build_public_url(marker_path)
                else:
                    marker_path_abs = Path(settings.STORAGE_BASE_PATH) / marker_path
                    marker_url = build_public_url(marker_path_abs)
            except Exception as e:
                logger.warning("marker_url_recalc_failed", error=str(e), marker_path=ar_content.marker_path)
        
        if not marker_url:
            raise HTTPException(status_code=400, detail="Marker URL not available")
        
        # Recalculate photo URL
        photo_url = ar_content.photo_url
        if ar_content.photo_path:
            try:
                photo_path = Path(ar_content.photo_path)
                if photo_path.is_absolute():
                    photo_url = build_public_url(photo_path)
                else:
                    photo_path_abs = Path(settings.STORAGE_BASE_PATH) / photo_path
                    photo_url = build_public_url(photo_path_abs)
            except Exception as e:
                logger.warning("photo_url_recalc_failed", error=str(e), photo_path=ar_content.photo_path)
        
        if not photo_url:
            raise HTTPException(status_code=400, detail="Photo URL not available")
        
        # Get video URL (simplified - use ar_content.video_url first, fastest path)
        video_url = ar_content.video_url
        
        # If no video_url, try to recalculate from video_path
        if not video_url and ar_content.video_path:
            try:
                video_path = Path(ar_content.video_path)
                if video_path.is_absolute():
                    video_url = build_public_url(video_path)
                else:
                    video_path_abs = Path(settings.STORAGE_BASE_PATH) / video_path
                    video_url = build_public_url(video_path_abs)
            except Exception as e:
                logger.warning("video_url_recalc_failed", error=str(e), video_path=ar_content.video_path)
        
        # Only try scheduler if still no video (scheduler can be slow)
        if not video_url:
            try:
                from app.services.video_scheduler import get_active_video
                active_video_data = await get_active_video(ar_content.id, db)
                if active_video_data and active_video_data.get("video"):
                    video_url = active_video_data["video"].video_url
            except Exception as e:
                logger.warning("active_video_fetch_failed", error=str(e), ar_content_id=ar_content.id)
        
        if not video_url:
            raise HTTPException(status_code=400, detail="Video not available for AR content")
        
        logger.info("ar_viewer_urls_prepared",
                   unique_id=unique_id,
                   marker_url=marker_url,
                   photo_url=photo_url,
                   video_url=video_url)
        
        # Increment views_count (simple increment, don't block)
        try:
            ar_content.views_count = (ar_content.views_count or 0) + 1
            await db.commit()
            await db.refresh(ar_content)
            logger.info("views_count_incremented", 
                       ar_content_id=ar_content.id, 
                       views_count=ar_content.views_count)
        except Exception as e:
            logger.warning("failed_to_increment_views", error=str(e))
            # Don't fail the request if view count increment fails
        
        # Return simple HTML (template will be used via html route)
        # This endpoint is called from html route which has proper request object
        import html as html_escape
        
        # Use relative paths for viewer - browser will use same origin as the page
        # This works correctly with port forwarding (443 -> 8000)
        marker_url_for_viewer = marker_url if (marker_url or "").startswith("/") else "/" + (marker_url or "")
        video_url_for_viewer = video_url if (video_url or "").startswith("/") else "/" + (video_url or "")
        
        diagnose_mode_str = "true" if diagnose else "false"
        # Скрипты загружаются динамически в JavaScript, чтобы не блокировать страницу
        html_content = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>AR Viewer - {html_escape.escape(ar_content.order_number)}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; overflow: hidden; background: #000; }}
        #ar-container {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; }}
        #loading {{ position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); color: white; font-size: 18px; text-align: center; z-index: 1000; }}
        #instructions {{ position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); background: rgba(0, 0, 0, 0.7); color: white; padding: 15px 25px; border-radius: 10px; font-size: 14px; text-align: center; max-width: 90%; z-index: 1000; }}
        .hidden {{ display: none; }}
    </style>
</head>
<body>
    <div id="loading">
        <div>AR просмотр</div>
        <div style="font-size: 14px; margin-top: 10px; opacity: 0.9;">Нажмите кнопку ниже — браузер запросит доступ к камере и покажет «Разрешить»</div>
        <button id="start-camera-btn" type="button" style="margin-top: 20px; padding: 14px 28px; min-height: 48px; font-size: 18px; background: #1a73e8; color: white; border: none; border-radius: 8px; cursor: pointer; display: inline-block; touch-action: manipulation; -webkit-tap-highlight-color: transparent;">Запустить камеру</button>
        <div id="start-camera-hint" style="font-size: 12px; margin-top: 14px; opacity: 0.7;">Ссылка должна открываться по HTTPS. Если кнопка «Разрешить» не видна — проверьте иконку камеры в адресной строке или настройки сайта.</div>
    </div>
    <div id="instructions" class="hidden">Наведите камеру на портрет</div>
    <div id="ar-container"></div>
    <video id="camera-preview" class="hidden" autoplay playsinline muted style="position:fixed;top:0;left:0;width:100%;height:100%;object-fit:cover;z-index:500;"></video>
    <div id="camera-preview-overlay" class="hidden" style="position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);color:white;text-align:center;z-index:501;pointer-events:none;"><div>Загрузка AR...</div><div style="font-size:14px;margin-top:10px;opacity:0.9;">Подождите</div></div>
    <div id="debug-log" style="position:fixed;bottom:0;left:0;right:0;max-height:40vh;overflow-y:auto;background:rgba(0,0,0,0.9);color:#0f0;font-size:11px;font-family:monospace;padding:8px;z-index:9999;display:block;"></div>
    <script>
        // Debug logger - shows on screen
        var debugEl = document.getElementById('debug-log');
        var originalLog = console.log;
        var originalError = console.error;
        var originalWarn = console.warn;
        function dbg(prefix, args) {{
            var msg = prefix + ': ' + Array.prototype.slice.call(args).map(function(a) {{
                if (a === null) return 'null';
                if (a === undefined) return 'undefined';
                if (typeof a === 'object') try {{ return JSON.stringify(a).substring(0,100); }} catch(e) {{ return String(a); }}
                return String(a);
            }}).join(' ');
            if (debugEl) {{
                var line = document.createElement('div');
                line.textContent = new Date().toLocaleTimeString() + ' ' + msg;
                if (prefix === 'ERR') line.style.color = '#f44';
                if (prefix === 'WARN') line.style.color = '#fa0';
                debugEl.appendChild(line);
                debugEl.scrollTop = debugEl.scrollHeight;
            }}
        }}
        console.log = function() {{ dbg('LOG', arguments); originalLog.apply(console, arguments); }};
        console.error = function() {{ dbg('ERR', arguments); originalError.apply(console, arguments); }};
        console.warn = function() {{ dbg('WARN', arguments); originalWarn.apply(console, arguments); }};
        window.onerror = function(msg, url, line) {{ dbg('ERR', ['Global:', msg, 'at line', line]); }};
        console.log('Debug panel initialized');
        
        const PORTRAIT_UID = "{unique_id}";
        const API_BASE = window.location.origin;
        const MARKER_URL = "{html_escape.escape(marker_url_for_viewer)}";
        const VIDEO_URL = "{html_escape.escape(video_url_for_viewer)}";
        const DIAGNOSE_MODE_STR = "{diagnose_mode_str}";
        const DIAGNOSE_MODE = (typeof DIAGNOSE_MODE_STR !== 'undefined' && DIAGNOSE_MODE_STR === 'true');
        var lastArStage = 'start_begin';
        
        function loadScript(src) {{
            return new Promise(function(resolve, reject) {{
                var s = document.createElement('script');
                s.src = src;
                s.onload = resolve;
                s.onerror = function() {{ reject(new Error('Failed to load: ' + src)); }};
                document.head.appendChild(s);
            }});
        }}
        function loadAllScripts() {{
            // Use CDN for MindAR v1.1.5 - this version has IIFE bundle that sets window.MINDAR
            // Note: v1.2.5 uses ES modules and doesn't work with script tags
            // MindAR requires WebGL backend (CPU backend NOT supported)
            console.log('Loading Three.js from CDN...');
            return loadScript('https://cdn.jsdelivr.net/npm/three@0.147.0/build/three.min.js')
                .then(function() {{
                    console.log('THREE loaded:', !!window.THREE);
                    window.three = window.THREE;
                    console.log('Loading MindAR v1.1.5 from CDN...');
                    return loadScript('https://cdn.jsdelivr.net/npm/mind-ar@1.1.5/dist/mindar-image-three.prod.js');
                }})
                .then(function() {{
                    console.log('MindAR loaded. MINDAR:', !!window.MINDAR, 'IMAGE:', !!(window.MINDAR && window.MINDAR.IMAGE));
                    if (window.MINDAR && window.MINDAR.IMAGE) {{
                        console.log('MindARThree:', typeof window.MINDAR.IMAGE.MindARThree);
                        console.log('MINDAR.IMAGE keys:', Object.keys(window.MINDAR.IMAGE).join(','));
                    }}
                }});
        }}
        
        async function initAR() {{
            var loadingEl = document.getElementById('loading');
            var isMobile = /Mobile|Android|iP(hone|od)/.test(navigator.userAgent);
            // AR works on both mobile and desktop - desktop is often more stable
            console.log('Device type:', isMobile ? 'mobile' : 'desktop');
            
            // Early WebGL check - TensorFlow.js requires specific WebGL features
            loadingEl.innerHTML = '<div>Проверка WebGL...</div>';
            var webglInfo = {{ ok: false, version: null, renderer: '', extensions: [] }};
            try {{
                var testCanvas = document.createElement('canvas');
                var gl = testCanvas.getContext('webgl2') || testCanvas.getContext('webgl') || testCanvas.getContext('experimental-webgl');
                if (gl) {{
                    webglInfo.ok = true;
                    webglInfo.version = gl.getParameter(gl.VERSION);
                    var dbg = gl.getExtension('WEBGL_debug_renderer_info');
                    if (dbg) webglInfo.renderer = gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL);
                    // TensorFlow.js requires these extensions
                    var requiredExt = ['OES_texture_float', 'WEBGL_lose_context'];
                    requiredExt.forEach(function(ext) {{
                        if (gl.getExtension(ext)) webglInfo.extensions.push(ext);
                    }});
                    // Clean up
                    var loseCtx = gl.getExtension('WEBGL_lose_context');
                    if (loseCtx) loseCtx.loseContext();
                }}
            }} catch (e) {{ console.warn('WebGL check error:', e); }}
            console.log('WebGL info:', webglInfo);
            if (!webglInfo.ok) {{
                var hint = isMobile 
                    ? 'Этот браузер не поддерживает WebGL. Попробуйте Chrome или Safari.'
                    : 'WebGL отключен. Включите аппаратное ускорение в настройках браузера.';
                throw new Error('<b>WebGL недоступен</b><br><br>' + hint);
            }}
            
            loadingEl.innerHTML = '<div>Загрузка библиотек AR...</div><div style="font-size: 14px; margin-top: 10px; opacity: 0.7;">Подождите</div>';
            try {{
                await loadAllScripts();
            }} catch (loadErr) {{
                console.error('Scripts load error:', loadErr);
                throw new Error('Не удалось загрузить библиотеки AR. Проверьте интернет.');
            }}
            try {{
                if (!window.MINDAR || !window.MINDAR.IMAGE) {{
                    throw new Error('Библиотека AR не загрузилась. Проверьте интернет и обновите страницу.');
                }}
                const MindARThree = window.MINDAR.IMAGE.MindARThree;
                if (typeof MindARThree !== 'function') {{
                    throw new Error('MindARThree недоступен. Обновите страницу.');
                }}
                loadingEl.innerHTML = '<div>Загрузка маркера...</div><div style="font-size: 14px; margin-top: 10px; opacity: 0.7;">Подождите</div>';
                var markerFullUrl = MARKER_URL.startsWith('http') ? MARKER_URL : (API_BASE + (MARKER_URL.startsWith('/') ? '' : '/') + MARKER_URL);
                console.log('Marker URL:', markerFullUrl);
                console.log('API_BASE:', API_BASE, 'MARKER_URL:', MARKER_URL);
                try {{
                    console.log('Fetching marker...');
                    var markerResp = await fetch(markerFullUrl, {{ mode: 'cors', cache: 'default' }});
                    console.log('Marker response:', markerResp.status, markerResp.ok);
                    if (!markerResp.ok) throw new Error('Маркер не загружен: ' + markerResp.status);
                }} catch (preloadErr) {{
                    console.error('Marker preload error:', preloadErr);
                    throw new Error('Не удалось загрузить маркер. Проверьте интернет и обновите страницу.');
                }}
                loadingEl.innerHTML = '<div>Подготовка нейросети...</div><div style="font-size: 14px; margin-top: 10px; opacity: 0.7;">На телефоне может занять 1–2 мин</div>';
                loadingEl.style.display = 'block';
                loadingEl.classList.remove('hidden');
                var tf = window.MINDAR && window.MINDAR.IMAGE && window.MINDAR.IMAGE.tf;
                if (tf) {{
                    try {{
                        // MindAR requires WebGL backend - CPU backend is NOT supported
                        // because MindAR uses WebGL-specific APIs (texData, gpgpu, compileAndRun)
                        if (typeof tf.ready === 'function') {{
                            await tf.ready();
                        }}
                        // Check if WebGL backend is available
                        var backend = tf.getBackend && tf.getBackend();
                        console.log('TensorFlow.js backend:', backend);
                        if (!backend || (backend !== 'webgl' && backend !== 'webgl2')) {{
                            throw new Error('WebGL не поддерживается. MindAR требует WebGL для работы.');
                        }}
                        // Disable WEBGL_PACK for better compatibility
                        if (tf.env && typeof tf.env === 'function') {{
                            var env = tf.env();
                            if (env && env.set && typeof env.set === 'function') {{
                                env.set('WEBGL_PACK', false);
                            }}
                        }}
                        // Warmup TensorFlow.js
                        if (tf.ones && typeof tf.ones === 'function') {{
                            var w = tf.ones([1, 1]);
                            if (w && w.dispose) w.dispose();
                        }}
                        if (tf.nextFrame && typeof tf.nextFrame === 'function') await tf.nextFrame();
                        await new Promise(function(r) {{ setTimeout(r, 300); }});
                    }} catch (tfErr) {{
                        console.error('TensorFlow.js init error:', tfErr);
                        // TensorFlow.js WebGL failed even though basic WebGL works
                        // This usually means missing extensions or GPU driver issues
                        var tfHint = '';
                        if (webglInfo.ok) {{
                            tfHint = '<br><br><b>Диагностика:</b><br>' +
                                '• WebGL версия: ' + (webglInfo.version || 'неизвестно') + '<br>' +
                                '• GPU: ' + (webglInfo.renderer || 'неизвестно') + '<br>' +
                                '• Расширения: ' + (webglInfo.extensions.length ? webglInfo.extensions.join(', ') : 'не найдены') + '<br><br>' +
                                'TensorFlow.js требует специфичные WebGL расширения, которые не поддерживаются вашей видеокартой или драйверами.';
                        }}
                        var webglHint = isMobile 
                            ? '<br><br>Попробуйте Chrome или Safari на этом устройстве.'
                            : '<br><br><b>Рекомендации:</b><br>• Обновите драйверы видеокарты<br>• Попробуйте Firefox или Edge<br>• Включите аппаратное ускорение в настройках браузера';
                        throw new Error('<b>TensorFlow.js не смог использовать WebGL</b>' + tfHint + webglHint);
                    }}
                }}
                var arContainer = document.getElementById("ar-container");
                loadingEl.style.display = 'none';
                loadingEl.classList.add('hidden');
                if (arContainer.offsetWidth === 0 || arContainer.offsetHeight === 0) {{
                    loadingEl.style.display = 'block';
                    loadingEl.classList.remove('hidden');
                    loadingEl.innerHTML = '<div>Ошибка: контейнер AR не имеет размера.</div><button type="button" onclick="location.reload()" style="margin-top:12px;padding:8px 16px;">Обновить</button>';
                    throw new Error('Контейнер AR не имеет размера. Обновите страницу.');
                }}
                console.log('Creating MindARThree with marker:', markerFullUrl);
                console.log('arContainer:', arContainer, 'tagName:', arContainer ? arContainer.tagName : 'null');
                console.log('arContainer size:', arContainer ? arContainer.offsetWidth + 'x' + arContainer.offsetHeight : 'null');
                console.log('arContainer style:', arContainer ? arContainer.style : 'null');
                
                if (!arContainer) {{
                    throw new Error('AR container element not found');
                }}
                
                var mindarThree;
                try {{
                    mindarThree = new MindARThree({{
                        container: arContainer,
                        imageTargetSrc: markerFullUrl,
                        maxTrack: 1,
                        uiLoading: "no",
                        uiScanning: "no",
                        uiError: "no"
                    }});
                    console.log('MindARThree created successfully');
                }} catch (createErr) {{
                    console.error('MindARThree constructor error:', createErr);
                    console.error('Error message:', createErr && createErr.message);
                    console.error('Error stack:', createErr && createErr.stack);
                    throw createErr;
                }}
                
                // Always wrap internal methods to track progress (not just in DIAGNOSE_MODE)
                ['_startVideo', '_startAR'].forEach(function(name) {{
                    if (mindarThree[name] && typeof mindarThree[name] === 'function') {{
                        var orig = mindarThree[name].bind(mindarThree);
                        mindarThree[name] = function() {{
                            var t0 = Date.now();
                            console.log('MindAR stage:', name, 'started');
                            lastArStage = name + '_started';
                            return orig().then(function() {{ 
                                console.log('MindAR stage:', name, 'completed in', Date.now() - t0, 'ms');
                                lastArStage = name + '_done'; 
                                if (DIAGNOSE_MODE) sendDiagnostic(name, Date.now() - t0); 
                            }}, function(e) {{ 
                                console.error('MindAR stage:', name, 'failed after', Date.now() - t0, 'ms', e);
                                lastArStage = name + '_error';
                                if (DIAGNOSE_MODE) sendDiagnostic(name + '_error', Date.now() - t0, e); 
                                throw e; 
                            }});
                        }};
                    }}
                }});
                
                const {{renderer, scene, camera}} = mindarThree;
                
                const video = document.createElement('video');
                video.src = VIDEO_URL;
                video.loop = true;
                video.muted = true;
                video.playsInline = true;
                video.preload = "auto";
                
                const texture = new THREE.VideoTexture(video);
                texture.minFilter = THREE.LinearFilter;
                texture.magFilter = THREE.LinearFilter;
                
                const geometry = new THREE.PlaneGeometry(1, 0.5625);
                const material = new THREE.MeshBasicMaterial({{ map: texture, transparent: true, side: THREE.DoubleSide }});
                const plane = new THREE.Mesh(geometry, material);
                
                const anchor = mindarThree.addAnchor(0);
                anchor.group.add(plane);
                
                anchor.onTargetFound = () => {{
                    video.play().catch(e => console.error('Video play error:', e));
                    document.getElementById('instructions').classList.add('hidden');
                }};
                
                anchor.onTargetLost = () => {{
                    video.pause();
                }};
                
                await new Promise(function(r) {{ requestAnimationFrame(r); }});
                
                // Pre-check camera access before starting MindAR
                // MindAR v1.1.5 calls reject() without error message on camera failures
                loadingEl.style.display = 'block';
                loadingEl.classList.remove('hidden');
                loadingEl.innerHTML = '<div>Запрос доступа к камере...</div><div style="font-size: 14px; margin-top: 10px; opacity: 0.7;">Нажмите «Разрешить» в диалоге браузера</div>';
                
                console.log('Pre-checking camera access...');
                try {{
                    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {{
                        throw new Error('Браузер не поддерживает доступ к камере. Используйте Chrome, Safari или Firefox.');
                    }}
                    var testStream = await navigator.mediaDevices.getUserMedia({{ 
                        video: {{ facingMode: 'environment' }}, 
                        audio: false 
                    }});
                    console.log('Camera access granted');
                    // Stop test stream - MindAR will request its own
                    testStream.getTracks().forEach(function(t) {{ t.stop(); }});
                }} catch (camErr) {{
                    var camName = (camErr && camErr.name) || '';
                    var camMsg = (camErr && camErr.message) || String(camErr);
                    console.error('Camera pre-check error:', camName, camMsg);
                    if (camName === 'NotAllowedError' || camMsg.indexOf('denied') >= 0 || camMsg.indexOf('Permission') >= 0) {{
                        throw new Error('Доступ к камере запрещён. Разрешите камеру в настройках браузера и обновите страницу.');
                    }}
                    if (camName === 'NotFoundError' || camMsg.indexOf('not found') >= 0) {{
                        throw new Error('Камера не найдена. Убедитесь, что устройство имеет камеру.');
                    }}
                    if (camName === 'NotReadableError' || camMsg.indexOf('in use') >= 0) {{
                        throw new Error('Камера занята другим приложением. Закройте другие приложения и обновите страницу.');
                    }}
                    throw new Error('Не удалось получить доступ к камере: ' + camMsg);
                }}
                
                loadingEl.innerHTML = '<div>Запуск AR-трекинга...</div><div style="font-size: 14px; margin-top: 10px; opacity: 0.7;">Подождите до 2 мин</div>';
                var loadStartTime = Date.now();
                var longLoadHint = setTimeout(function() {{
                    if (loadingEl && loadingEl.style.display !== 'none') {{
                        var elapsed = Math.round((Date.now() - loadStartTime) / 1000);
                        loadingEl.innerHTML = '<div>Инициализация нейросети...</div>' +
                            '<div style="font-size: 14px; margin-top: 10px; opacity: 0.8;">Прошло ' + elapsed + ' сек. На мобильных может занять 2-5 минут.</div>' +
                            '<div style="font-size: 12px; margin-top: 8px; opacity: 0.6;">Не закрывайте страницу. Если долго — попробуйте на компьютере.</div>';
                    }}
                }}, 25000);
                // Update loading message every 30 seconds
                var loadingInterval = setInterval(function() {{
                    if (loadingEl && loadingEl.style.display !== 'none') {{
                        var elapsed = Math.round((Date.now() - loadStartTime) / 1000);
                        loadingEl.innerHTML = '<div>Инициализация нейросети...</div>' +
                            '<div style="font-size: 14px; margin-top: 10px; opacity: 0.8;">Прошло ' + elapsed + ' сек. Пожалуйста, подождите.</div>' +
                            '<div style="font-size: 12px; margin-top: 8px; opacity: 0.6;">GPU: ' + (webglInfo.renderer || 'неизвестно') + '</div>';
                    }}
                }}, 30000);
                var startTimeout = isMobile ? 180000 : 60000;  // 3 min mobile, 1 min desktop
                if (DIAGNOSE_MODE) sendDiagnostic('start_begin', 0);
                var startT0 = Date.now();
                
                console.log('Calling mindarThree.start()...');
                var startPromise = mindarThree.start().then(function() {{
                    console.log('mindarThree.start() completed successfully');
                }}).catch(function(err) {{
                    console.error('mindarThree.start() error:', err, JSON.stringify(err));
                    throw err;
                }});
                var timeoutPromise = new Promise(function(_, reject) {{
                    setTimeout(function() {{
                        if (DIAGNOSE_MODE) sendDiagnostic('start_timeout', startTimeout, {{ message: 'Timeout ' + (startTimeout/1000) + 's', stage: lastArStage }});
                        console.error('AR timeout at stage:', lastArStage);
                        var stageText, stageHint;
                        if (lastArStage === 'start_begin' || lastArStage === '_startVideo_started') {{
                            stageText = 'запуск камеры';
                            stageHint = 'Камера не отвечает. Закройте другие приложения и обновите страницу.';
                        }} else if (lastArStage === '_startVideo_done' || lastArStage === '_startAR_started') {{
                            stageText = 'инициализация нейросети';
                            stageHint = 'GPU ' + (webglInfo.renderer || 'этого устройства') + ' не справляется с компиляцией WebGL шейдеров за ' + (startTimeout/1000) + ' сек. Это известное ограничение MindAR.';
                        }} else {{
                            stageText = lastArStage || 'неизвестно';
                            stageHint = 'Попробуйте другой браузер.';
                        }}
                        var msg = '<b>Таймаут на этапе: ' + stageText + '</b><br><br>' + stageHint;
                        if (isMobile) msg += '<br><br><b>Рекомендация:</b> откройте эту ссылку на компьютере в Chrome — там AR работает стабильно.';
                        reject(new Error(msg));
                    }}, startTimeout);
                }});
                try {{
                    await Promise.race([startPromise, timeoutPromise]);
                    clearTimeout(longLoadHint);
                    clearInterval(loadingInterval);
                    if (DIAGNOSE_MODE) sendDiagnostic('start_complete', Date.now() - startT0);
                }} catch (startErr) {{
                    clearTimeout(longLoadHint);
                    clearInterval(loadingInterval);
                    if (DIAGNOSE_MODE) sendDiagnostic('start_error', Date.now() - startT0, startErr);
                    console.error('mindarThree.start error:', startErr);
                    var name = (startErr && startErr.name) || '';
                    var msg = (startErr && startErr.message) || '';
                    // MindAR v1.1.5 sometimes rejects with empty object {{}} - provide meaningful message
                    if (!msg && startErr && typeof startErr === 'object' && Object.keys(startErr).length === 0) {{
                        msg = 'MindAR не смог запустить камеру. Возможные причины: камера занята, браузер не поддерживает AR, или устройство несовместимо.';
                    }}
                    if (!msg) msg = String(startErr);
                    if (name === 'NotAllowedError' || (msg && (msg.indexOf('Permission') >= 0 || msg.indexOf('denied') >= 0))) {{
                        throw new Error('Доступ к камере запрещён. Разрешите камеру для этого сайта в настройках браузера и обновите страницу.');
                    }}
                    if (name === 'NotFoundError' || (msg && msg.indexOf('not found') >= 0)) {{
                        throw new Error('Камера не найдена. Подключите камеру или откройте на устройстве с камерой.');
                    }}
                    if (msg && msg.indexOf('Таймаут') >= 0) {{
                        throw new Error(msg);
                    }}
                    if (msg && (msg.indexOf('WebGL') >= 0 || msg.indexOf('webgl') >= 0)) {{
                        throw new Error('WebGL не поддерживается в этом окружении. Попробуйте другой браузер (Chrome с GPU) или устройство с поддержкой WebGL.');
                    }}
                    throw new Error('Не удалось запустить AR. ' + (msg || 'Неизвестная ошибка. Попробуйте другой браузер.'));
                }}
                loadingEl.classList.add('hidden');
                loadingEl.style.display = 'none';
                stopCameraPreview();
                var instructionsEl = document.getElementById('instructions');
                instructionsEl.classList.remove('hidden');
                instructionsEl.style.display = 'block';
                
                try {{
                    renderer.setAnimationLoop(function() {{
                        renderer.render(scene, camera);
                    }});
                }} catch (loopErr) {{
                    console.error('setAnimationLoop error:', loopErr);
                    throw new Error('Ошибка отрисовки AR. ' + (loopErr.message || String(loopErr)));
                }}
                trackARSession(PORTRAIT_UID);
            }} catch (error) {{
                console.error('AR initialization error:', error);
                if (DIAGNOSE_MODE) sendDiagnostic('init_error', 0, error);
                showError(error);
            }}
        }}
        
        function stopCameraPreview() {{
            if (window._arPreviewStream) {{
                window._arPreviewStream.getTracks().forEach(function(t) {{ t.stop(); }});
                window._arPreviewStream = null;
            }}
            var prev = document.getElementById('camera-preview');
            if (prev) {{ prev.srcObject = null; prev.classList.add('hidden'); }}
            var over = document.getElementById('camera-preview-overlay');
            if (over) over.classList.add('hidden');
        }}
        
        function showError(error) {{
            stopCameraPreview();
            if (typeof DIAGNOSE_MODE !== 'undefined' && DIAGNOSE_MODE && typeof sendDiagnostic === 'function') {{
                sendDiagnostic('show_error', 0, error);
            }}
            var msg = error && (error.message || String(error));
            var loading = document.getElementById('loading');
            loading.style.display = 'block';
            loading.style.position = 'fixed';
            loading.style.top = '50%';
            loading.style.left = '50%';
            loading.style.transform = 'translate(-50%, -50%)';
            loading.classList.remove('hidden');
            var hint = 'Обновите страницу или нажмите «Повторить».';
            if (msg && (msg.indexOf('timeout') >= 0 || msg.indexOf('Таймаут') >= 0 || msg.indexOf('load timeout') >= 0))
                hint = 'Загрузка прервалась по времени. Проверьте интернет (туннель может быть медленным), подождите и нажмите «Повторить».';
            else if (msg && (msg.indexOf('маркер') >= 0 || msg.indexOf('marker') >= 0 || msg.indexOf('fetch') >= 0))
                hint = 'Маркер не загрузился. Проверьте интернет и доступность ссылки, затем нажмите «Повторить».';
            loading.innerHTML = '<div style="color: #ff4444; font-weight: bold;">Ошибка загрузки AR</div>' +
                '<div style="font-size: 14px; margin-top: 12px; text-align: left; line-height: 1.6;">' + (msg || 'Неизвестная ошибка') + '</div>' +
                '<p style="font-size: 12px; margin-top: 12px; opacity: 0.8;">' + hint + '</p>' +
                '<button type="button" onclick="location.reload()" style="margin-top: 16px; padding: 10px 20px; background: #333; color: #fff; border: none; border-radius: 8px; font-size: 16px;">Повторить</button>' +
                '<style>code {{ background: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 3px; }}</style>';
        }}
        
        function trackARSession(portraitId) {{
            const sessionId = generateUUID();
            fetch(`${{API_BASE}}/api/analytics/mobile/sessions`, {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{
                    session_id: sessionId,
                    ar_content_unique_id: portraitId,
                    user_agent: navigator.userAgent,
                    device_type: /Mobile|Android|iP(hone|od)/.test(navigator.userAgent) ? 'mobile' : 'desktop'
                }})
            }}).catch(e => console.error('Session tracking error:', e));
        }}
        
        function generateUUID() {{
            return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {{
                const r = Math.random() * 16 | 0;
                const v = c === 'x' ? r : (r & 0x3 | 0x8);
                return v.toString(16);
            }});
        }}
        
        function sendDiagnostic(event, durationMs, err) {{
            if (!DIAGNOSE_MODE) return;
            var body = {{ event: event, duration_ms: durationMs, user_agent: navigator.userAgent, ar_content_unique_id: PORTRAIT_UID }};
            if (err) body.error = (err && err.message) || String(err);
            fetch(API_BASE + '/api/analytics/ar-diagnostic', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify(body)
            }}).catch(function(e) {{ console.error('Diagnostic send error:', e); }});
        }}
        
        window.onerror = function(msg, url, line, col, err) {{
            var text = (err && err.message) || msg || 'Неизвестная ошибка';
            showError({{ message: text + (line ? ' (строка ' + line + ')' : '') }});
        }};
        window.addEventListener('unhandledrejection', function(e) {{
            var err = e.reason;
            var msg = (err && (err.message || String(err))) || 'Необработанная ошибка';
            console.error('Unhandled rejection:', err);
            if (typeof sendDiagnostic !== 'undefined' && DIAGNOSE_MODE) sendDiagnostic('unhandled_rejection', 0, err);
            showError({{ message: msg }});
            e.preventDefault();
        }});
        (function() {{
            console.log('AR viewer script loaded');
            var btn = document.getElementById('start-camera-btn');
            var loadingEl = document.getElementById('loading');
            console.log('Button found:', !!btn, 'Loading found:', !!loadingEl);
            function onStartClick(e) {{
                console.log('Button clicked!', e ? e.type : 'no event');
                if (e && e.type === 'touchend') e.preventDefault();
                if (!btn) return;
                if (btn.disabled && btn.textContent.indexOf('Запрос') >= 0) return;
                if (!loadingEl) {{ console.error('loading element not found'); showError({{ message: 'Ошибка загрузки страницы. Обновите страницу.' }}); return; }}
                try {{
                    btn.disabled = true;
                    btn.textContent = 'Запрос камеры...';
                    loadingEl.innerHTML = '<div>Запрос доступа к камере...</div><div style="font-size: 14px; margin-top: 10px; opacity: 0.7;">Нажмите «Разрешить» в окне браузера</div>';
                }} catch (err) {{
                    console.error('onStartClick init:', err);
                    showError({{ message: (err && err.message) || String(err) }});
                    btn.disabled = false;
                    btn.textContent = 'Запустить камеру';
                    return;
                }}
                // Don't request camera here - let MindAR handle it
                // This avoids conflicts with multiple camera streams
                console.log('Starting AR directly (MindAR will request camera)...');
                loadingEl.innerHTML = '<div>Загрузка AR...</div><div style="font-size: 14px; margin-top: 10px; opacity: 0.7;">MindAR запросит камеру</div>';
                loadingEl.style.display = 'block';
                btn.textContent = 'Загрузка...';
                initAR();
            }}
            if (btn) {{
                console.log('Adding event listeners to button');
                btn.addEventListener('click', onStartClick);
                btn.addEventListener('touchend', function(e) {{ console.log('touchend!'); onStartClick(e); }}, {{ passive: false }});
                btn.style.cursor = 'pointer';
                btn.style.touchAction = 'manipulation';
                btn.style.border = '3px solid green';  // Visual indicator that JS is working
            }} else {{
                console.error('Button not found!');
            }}
            // AR works on both mobile and desktop - no restrictions needed
            window.addEventListener('load', function() {{
                console.log('Page loaded, AR ready on', /Mobile|Android|iP(hone|od)/.test(navigator.userAgent) ? 'mobile' : 'desktop');
            }});
        }})();
    </script>
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
    Validate AR marker quality and provide detailed information.
    
    Returns validation results including:
    - Features count
    - Validation warnings
    - Marker quality assessment
    - Recommendations for improvement
    """
    try:
        ar_content = await db.get(ARContent, ar_content_id)
        if not ar_content:
            raise HTTPException(status_code=404, detail="AR content not found")
        
        if not ar_content.marker_path:
            raise HTTPException(
                status_code=400, 
                detail="Marker not generated yet. Please regenerate media first."
            )
        
        # Validate marker file
        from app.services.mindar_generator import mindar_generator
        marker_path = Path(ar_content.marker_path)
        
        if not marker_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Marker file not found at path: {ar_content.marker_path}"
            )
        
        validation_result = mindar_generator.validate_marker_file(marker_path)
        
        # Get marker metadata if available
        marker_metadata = ar_content.marker_metadata or {}
        features_count = validation_result.get("features_count", 0) or marker_metadata.get("features_count", 0)
        
        # Assess quality
        quality_assessment = "excellent"
        recommendations = []
        
        if features_count == 0:
            quality_assessment = "invalid"
            recommendations.append("Marker has no features - AR tracking will not work")
            recommendations.append("Check if Node.js and MindAR dependencies are installed")
            recommendations.append("Try regenerating the marker with a higher quality image")
        elif features_count < 10:
            quality_assessment = "poor"
            recommendations.append(f"Marker has very few features ({features_count}) - tracking will be unreliable")
            recommendations.append("Use an image with more contrast and detail")
            recommendations.append("Ensure good lighting when capturing the marker")
        elif features_count < 50:
            quality_assessment = "fair"
            recommendations.append(f"Marker has few features ({features_count}) - tracking quality may be reduced")
            recommendations.append("Consider using a higher resolution image")
            recommendations.append("Ensure the image has good contrast and sharp edges")
        elif features_count < 200:
            quality_assessment = "good"
            recommendations.append(f"Marker has {features_count} features - tracking should work well")
        else:
            quality_assessment = "excellent"
            recommendations.append(f"Marker has {features_count} features - excellent tracking quality")
        
        # Add warnings to recommendations
        for warning in validation_result.get("warnings", []):
            recommendations.append(f"Warning: {warning}")
        
        logger.info("marker_validation_requested",
                   ar_content_id=ar_content_id,
                   features_count=features_count,
                   quality=quality_assessment,
                   is_valid=validation_result.get("is_valid", False))
        
        return {
            "ar_content_id": ar_content_id,
            "order_number": ar_content.order_number,
            "marker_url": ar_content.marker_url,
            "marker_path": ar_content.marker_path,
            "validation": {
                "is_valid": validation_result.get("is_valid", False),
                "features_count": features_count,
                "descriptors_count": validation_result.get("descriptors_count", 0),
                "width": validation_result.get("width"),
                "height": validation_result.get("height"),
                "image_size": validation_result.get("image_size"),
                "warnings": validation_result.get("warnings", []),
                "quality_assessment": quality_assessment
            },
            "metadata": marker_metadata,
            "recommendations": recommendations,
            "status": "ready" if validation_result.get("is_valid", False) else "needs_attention"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("marker_validation_error", 
                    error=str(e), 
                    ar_content_id=ar_content_id,
                    exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to validate marker: {str(e)}"
        )


# Endpoint to get marker file by unique_id
@router.get("/ar-content/marker/{unique_id}", tags=["AR Content"])
async def get_ar_marker(unique_id: str, db: AsyncSession = Depends(get_db)):
    """Get AR marker file by unique_id"""
    try:
        # Validate UUID format
        parsed_uuid = UUID(unique_id)
        
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
        parsed_uuid = UUID(unique_id)
        
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