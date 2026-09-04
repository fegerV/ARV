"""
AR Content API routes with Company → Project → AR Content hierarchy.
"""
from uuid import uuid4, UUID
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query, BackgroundTasks, Request
import shutil
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete as sa_delete, select, func, update as sa_update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
import structlog
import re
from datetime import datetime
import time

from app.services.thumbnail_service import thumbnail_service

# marker_service — ленивый импорт (cv2/numpy), не грузить при старте приложения
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
    save_uploaded_file,
    validate_photo_file,
)
from app.core.storage_providers import get_provider_for_company
from app.api.deps_authz import require_company_access
from app.api.routes.auth import get_current_active_user
from app.models.user import User

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


async def generate_order_number(project_id: int, db: AsyncSession) -> str:
    """Generate unique order number in format ORD-YYYYMMDD-XXXX per project."""
    now = datetime.now()
    date_str = now.strftime("%Y%m%d")
    prefix = f"ORD-{date_str}-"
    
    stmt = (
        select(ARContent.order_number)
        .where(ARContent.project_id == project_id)
        .where(ARContent.order_number.like(prefix + "%"))
        .order_by(ARContent.order_number.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    last_order = result.scalar_one_or_none()
    
    if last_order:
        try:
            last_seq = int(last_order.rsplit("-", 1)[-1])
            next_seq = last_seq + 1
        except (ValueError, IndexError):
            next_seq = 1
    else:
        next_seq = 1
    
    return f"{prefix}{next_seq:04d}"


def validate_file_extension(filename: str, allowed_extensions: list) -> bool:
    """Validate file extension against allowed extensions"""
    ext = Path(filename).suffix.lower()[1:]  # Remove the dot
    return ext in allowed_extensions


def validate_file_size(file_size: int, max_size: int) -> bool:
    """Validate file size against maximum allowed size"""
    return file_size <= max_size


@router.get("/ar-content", response_model=ARContentList, tags=["AR Content"])
async def list_all_ar_content(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=1000, description="Number of items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all AR content across all companies and projects."""
    # Calculate offset from page and page_size
    skip = (page - 1) * page_size
    
    # Count total items
    count_stmt = select(func.count(ARContent.id))
    if not getattr(current_user, 'is_super_admin', False) and getattr(current_user, 'company_id', None) is not None:
        count_stmt = count_stmt.where(ARContent.company_id == getattr(current_user, 'company_id', None))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar_one()

    # Calculate total pages
    total_pages = (total + page_size - 1) // page_size  # Ceiling division

    # Get items with pagination, sorted by created_at DESC (newest first)
    stmt = select(ARContent).options(
        selectinload(ARContent.company), 
        selectinload(ARContent.project)
    ).order_by(ARContent.created_at.desc()).offset(skip).limit(page_size)
    if not getattr(current_user, 'is_super_admin', False) and getattr(current_user, 'company_id', None) is not None:
        stmt = stmt.where(ARContent.company_id == getattr(current_user, 'company_id', None))
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
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=1000, description="Number of items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all AR content across all companies and projects (route with trailing slash)."""
    # This is just a redirect to the main function
    return await list_all_ar_content(page=page, page_size=page_size, db=db, current_user=current_user)


@router.get("/companies/{company_id}/projects/{project_id}/ar-content", response_model=ARContentList, tags=["AR Content"])
async def list_ar_content(
    request: Request,
    company_id: int,
    project_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=1000, description="Number of items per page"),
    company: Company = Depends(require_company_access),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
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
    db: AsyncSession,
    background_tasks: Optional["BackgroundTasks"] = None,
):
    """Внутренняя функция для создания AR-контента"""
    t0 = time.perf_counter()
    logger.info("ar_content_create_start", company_id=company_id, project_id=project_id)

    created_files: list[str] = []
    success = False

    # Validate company and project relationship
    company, project = await validate_company_project(company_id, project_id, db)

    # Resolve storage provider for the company
    provider = await get_provider_for_company(company)
    from app.core.yandex_disk_provider import YandexDiskStorageProvider
    is_yd = isinstance(provider, YandexDiskStorageProvider)
    
    # Validate duration years
    if duration_years < 1:
        raise HTTPException(status_code=400, detail="duration_years must be >= 1")
    
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

    validate_photo_file(photo_file)

    if not validate_file_extension(video_file.filename, allowed_video_extensions):
        raise HTTPException(status_code=422, detail="Video must be MP4, WebM, or MOV")

    created_files: list[str] = []
    success = False

    try:
        # Generate unique identifier
        unique_id = str(uuid4())
        
        # Generate order number
        order_number = await generate_order_number(project_id, db)
        
        # Build local storage path (always needed for temp files / image analysis)
        storage_path = build_ar_content_storage_path(
            company_id=company_id,
            project_id=project_id,
            order_number=order_number,
            company_name=company.name,
            project_name=project.name
        )
        storage_path.mkdir(parents=True, exist_ok=True)
        created_files.append(str(storage_path))

        # Relative path used for Yandex Disk uploads
        from app.utils.slug_utils import generate_slug
        project_slug = generate_slug(project.name) or f"Project_{project_id}"
        from app.utils.ar_content import sanitize_filename
        order_folder = sanitize_filename(order_number, max_length=50)
        yd_relative_prefix = f"{project_slug}/{order_folder}"
        
        # Save photo
        photo_filename = f"photo{Path(photo_file.filename).suffix}"
        photo_path = storage_path / photo_filename
        if is_yd:
            # Save locally first (needed for image analysis), then upload to YD
            import tempfile as _tmpmod
            _tmp_photo = Path(_tmpmod.mkdtemp()) / photo_filename
            created_files.append(str(_tmp_photo))
            await save_uploaded_file(photo_file, _tmp_photo)
            yd_photo_ref = await provider.save_file(str(_tmp_photo), f"{yd_relative_prefix}/{photo_filename}")
            # Keep local copy for analysis
            shutil.copy2(str(_tmp_photo), str(photo_path))
        else:
            await save_uploaded_file(photo_file, photo_path)
            yd_photo_ref = None

        logger.info("ar_content_create_photo_saved", elapsed_s=round(time.perf_counter() - t0, 2))
        
        # Save video
        video_filename = f"video{Path(video_file.filename).suffix}"
        video_path = storage_path / video_filename
        if is_yd:
            yd_video_ref = await save_uploaded_file(
                video_file,
                video_path,
                provider=provider,
                relative_storage_path=f"{yd_relative_prefix}/{video_filename}",
            )
        else:
            await save_uploaded_file(video_file, video_path)
            yd_video_ref = None

        logger.info("ar_content_create_video_saved", elapsed_s=round(time.perf_counter() - t0, 2))

        # Resolve URLs depending on provider
        if is_yd:
            photo_url_val = yd_photo_ref or provider.get_public_url(f"{yd_relative_prefix}/{photo_filename}")
            video_url = yd_video_ref or provider.get_public_url(f"{yd_relative_prefix}/{video_filename}")
        else:
            photo_url_val = build_public_url(photo_path, provider=provider)
            video_url = build_public_url(video_path, provider=provider)
        
        # Generate QR code
        if is_yd:
            qr_code_url = await generate_qr_code(
                unique_id,
                Path(yd_relative_prefix),
                provider=provider,
                order_number=order_number,
            )
        else:
            qr_code_url = await generate_qr_code(
                unique_id,
                storage_path,
                provider=provider,
                order_number=order_number,
            )
        logger.info(
            "ar_content_create_storage_ready",
            elapsed_s=round(time.perf_counter() - t0, 2),
            storage_path=str(storage_path),
            photo_path=str(photo_path),
            video_path=str(video_path),
            photo_url=photo_url_val,
            video_url=video_url,
            qr_code_url=qr_code_url,
            storage_provider=company.storage_provider,
        )

        # Analyze photo quality and build recommendations (always uses local file)
        from app.services.marker_service import image_quality_analyzer
        image_quality = image_quality_analyzer.analyze_image_quality(str(photo_path))
        recommendations = image_quality_analyzer.build_image_recommendations(image_quality)
        photo_analysis: dict = {
            "metrics": image_quality,
            "recommendations": recommendations,
            "auto_enhanced": False,
        }

        marker_image_path = str(photo_path)
        if auto_enhance:
            if image_quality_analyzer.should_auto_enhance(image_quality):
                enhanced_photo_path = storage_path / "photo_enhanced.png"
                created_files.append(str(enhanced_photo_path))
                enhanced_path = image_quality_analyzer.enhance_image_for_marker(
                    image_path=str(photo_path),
                    output_path=str(enhanced_photo_path),
                )
                if enhanced_path:
                    marker_image_path = enhanced_path
                    enhanced_metrics = image_quality_analyzer.analyze_image_quality(enhanced_path)
                    photo_analysis.update(
                        {
                            "auto_enhanced": True,
                            "enhanced_metrics": enhanced_metrics,
                        }
                    )
                    # Upload enhanced version to YD
                    if is_yd:
                        await provider.save_file(
                            enhanced_path,
                            f"{yd_relative_prefix}/photo_enhanced.png",
                        )
            else:
                photo_analysis["auto_enhance_skipped_reason"] = "quality_above_threshold"

        # Paths stored in DB: for YD — yadisk:// refs, for local — absolute paths
        db_photo_path = yd_photo_ref if is_yd else str(photo_path)
        db_video_path = yd_video_ref if is_yd else str(video_path)
        db_qr_path = qr_code_url if is_yd else str(storage_path / "qr_code.png")

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
            photo_path=db_photo_path,
            photo_url=photo_url_val,
            video_path=db_video_path,
            video_url=video_url,
            qr_code_path=db_qr_path,
            qr_code_url=qr_code_url,
            status="pending"
        )
        
        db.add(ar_content)
        for attempt in range(3):
            try:
                await db.commit()
                break
            except IntegrityError:
                await db.rollback()
                if attempt == 2:
                    raise
                order_number = await generate_order_number(project_id, db)
                ar_content.order_number = order_number
        await db.refresh(ar_content)
        
        # Generate thumbnail (use enhanced image path when auto-enhance was applied)
        try:
            thumbnail_result = await thumbnail_service.generate_image_thumbnail(
                image_path=marker_image_path,
                company_id=company_id,
                storage_path=storage_path
            )
            
            if thumbnail_result.get("status") == "ready":
                thumb_url = thumbnail_result.get("thumbnail_url")
                thumb_local = thumbnail_result.get("thumbnail_path")
                if thumb_local and Path(thumb_local).exists():
                    created_files.append(thumb_local)
                    # For YD: upload generated thumbnail
                    if is_yd:
                        thumb_url = await provider.save_file(
                            thumb_local,
                            f"{yd_relative_prefix}/thumbnail.png",
                        )
                ar_content.thumbnail_url = thumb_url
                await db.commit()
                await db.refresh(ar_content)
                logger.info(
                    "photo_thumbnail_generation_saved",
                    ar_content_id=ar_content.id,
                    thumbnail_url=thumbnail_url,
                )
            else:
                logger.warning("photo_thumbnail_generation_failed", error=thumbnail_result.get("error"))
        except Exception as e:
            logger.error("photo_thumbnail_generation_exception", error=str(e))
        
        # Create video record
        video_record = Video(
            ar_content_id=ar_content.id,
            filename=video_filename,
            video_path=db_video_path,
            video_url=video_url,
            preview_url=video_url,
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

        # Запускаем фоновую генерацию превью видео
        if background_tasks is not None and video_record.video_path:
            from app.api.routes.videos import _generate_video_thumbnail_task
            background_tasks.add_task(
                _generate_video_thumbnail_task,
                video_record.id,
                video_record.video_path,
            )
            logger.info(
                "video_thumbnail_task_enqueued",
                video_id=video_record.id,
                video_path=video_record.video_path,
            )

        # ARCore: marker = photo image (no .mind generation)
        # Analyze quality and enrich metadata for Android app
        try:
            from app.services.marker_service import image_quality_analyzer
            from app.services.email_transport import send_email
            
            # Calculate quality score and determine status
            quality_score = image_quality_analyzer.calculate_quality_score(image_quality)
            marker_status = image_quality_analyzer.get_marker_status(quality_score)
            quality_issue_reason = image_quality_analyzer.get_quality_issue_reason(image_quality, quality_score)
            
            # Get image dimensions (lazy import cv2)
            import cv2
            img = cv2.imread(str(photo_path))
            if img is not None:
                height, width = img.shape[:2]
                aspect_ratio = round(width / height, 4) if height > 0 else 0.0
            else:
                width, height, aspect_ratio = 0, 0, 0.0
            
            # Build enriched marker_metadata for Android app
            marker_metadata = {
                "width": width,
                "height": height,
                "quality_score": quality_score,
                "aspect_ratio": aspect_ratio,
                "format": Path(photo_path).suffix.lower().lstrip("."),
                "sharpness": round(image_quality.get("sharpness", 0.0), 2),
                "contrast": round(image_quality.get("contrast", 0.0), 2),
                "edge_density": round(image_quality.get("edge_density", 0.0), 4),
                "brightness": round(image_quality.get("brightness", 0.0), 2),
                "recognition_probability": image_quality.get("recognition_probability"),
            }
            
            if quality_issue_reason:
                marker_metadata["quality_issue_reason"] = quality_issue_reason
            
            ar_content.marker_path = db_photo_path
            ar_content.marker_url = photo_url_val
            ar_content.marker_status = marker_status  # "ready" or "low_quality"
            ar_content.marker_metadata = marker_metadata
            ar_content.status = "ready"  # Content is always created regardless of quality
            
            await db.commit()
            await db.refresh(ar_content)
            
            logger.info(
                "marker_saved_from_photo",
                ar_content_id=ar_content.id,
                marker_url=ar_content.marker_url,
                marker_status=ar_content.marker_status,
                quality_score=quality_score,
            )
            
            # Send email notification if quality is low
            if marker_status == "low_quality":
                try:
                    subject = f"⚠️ AR Content Low Quality Warning: {ar_content.order_number}"
                    message = f"""
<html>
<body>
<h2>Warning: Low Quality AR Marker Detected</h2>
<p>AR content <strong>{ar_content.order_number}</strong> was created with a marker image that has low quality.</p>
<p><strong>Quality Score:</strong> {quality_score}/100 (threshold: {image_quality_analyzer.MIN_MARKER_QUALITY_SCORE})</p>
<p><strong>Issue:</strong> {quality_issue_reason or "Unknown"}</p>
<h3>Image Metrics:</h3>
<ul>
    <li>Resolution: {width}x{height}</li>
    <li>Sharpness: {marker_metadata['sharpness']}</li>
    <li>Contrast: {marker_metadata['contrast']}</li>
    <li>Edge Density: {marker_metadata['edge_density']}</li>
    <li>Brightness: {marker_metadata['brightness']}</li>
</ul>
<p><strong>Recommendations:</strong></p>
<ul>
    {"".join(f"<li>{r}</li>" for r in recommendations)}
</ul>
<p>Consider re-uploading a higher quality image for better AR tracking performance.</p>
<p>--<br>V-Portal Platform</p>
</body>
</html>
"""
                    # Send to admin and/or content creator
                    recipients = [settings.ADMIN_EMAIL]
                    if ar_content.customer_email:
                        recipients.append(ar_content.customer_email)
                    
                    send_email(
                        to_email=recipients,
                        subject=subject,
                        template_name="",  # Empty template name triggers plain HTML body usage
                        context={"message": message}
                    )
                    logger.info(
                        "low_quality_email_sent",
                        ar_content_id=ar_content.id,
                        recipients=recipients,
                    )
                except Exception as email_exc:
                    logger.error("low_quality_email_failed", error=str(email_exc))
            
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
                
                notification_subject = f"New AR Content Created: {ar_content.order_number}"
                notification_message = f"AR content '{ar_content.order_number}' has been successfully created and is ready for use."
                
                if marker_status == "low_quality":
                    notification_message += f" WARNING: Marker quality is low (score: {quality_score}/100). Consider re-uploading a better image."
                
                await create_notification(
                    db=db,
                    notification_type="ar_content_created",
                    subject=notification_subject,
                    message=notification_message,
                    company_id=company_id,
                    project_id=project_id,
                    ar_content_id=ar_content.id,
                    metadata={
                        "is_read": False,
                        "company_name": company_name,
                        "project_name": project_name,
                        "ar_content_name": ar_content.order_number,
                        "marker_status": marker_status,
                        "quality_score": quality_score,
                    }
                )
            except Exception as e:
                logger.warning("failed_to_create_notification", error=str(e))
        except Exception as e:
            logger.error("marker_save_exception", error=str(e))

        total_elapsed = round(time.perf_counter() - t0, 2)
        logger.info("ar_content_create_done", ar_content_id=ar_content.id, total_elapsed_s=total_elapsed)
        
        success = True
        return ARContentCreateResponse(
            id=ar_content.id,
            order_number=ar_content.order_number,
            public_link=build_unique_link(ar_content.unique_id),
            qr_code_url=ar_content.qr_code_url,
            photo_url=ar_content.photo_url,
            video_url=ar_content.video_url,
            photo_analysis=photo_analysis,
        )
    finally:
        if not success:
            try:
                await db.rollback()
            except Exception:
                pass
            for path in created_files:
                try:
                    p = Path(path)
                    if p.is_dir():
                        shutil.rmtree(p, ignore_errors=True)
                    elif p.exists():
                        p.unlink(missing_ok=True)
                except Exception:
                    pass


@router.post("/ar-content/{ar_content_id}/regenerate-media", tags=["AR Content"])
async def regenerate_media(
    request: Request,
    ar_content_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Regenerate preview thumbnail and marker for AR content."""
    ar_content = await db.get(ARContent, ar_content_id)
    if not ar_content:
        raise HTTPException(status_code=404, detail="AR content not found")

    if not getattr(current_user, 'is_super_admin', False) and getattr(current_user, 'company_id', None) is not None:
        if ar_content.company_id != getattr(current_user, 'company_id', None):
            raise HTTPException(status_code=403, detail="Access denied to this AR content")

    try:
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
    request: Request,
    company_id: int = Form(...),
    project_id: int = Form(...),
    customer_name: Optional[str] = Form(None),
    customer_phone: Optional[str] = Form(None),
    customer_email: Optional[str] = Form(None),
    duration_years: int = Form(30),
    auto_enhance: bool = Form(False),
    photo_file: UploadFile = File(...),
    video_file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create new AR content with photo and video files."""
    if not getattr(current_user, 'is_super_admin', False) and getattr(current_user, 'company_id', None) is not None:
        if company_id != getattr(current_user, 'company_id', None):
            raise HTTPException(status_code=403, detail="Access denied to this company")
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
        db=db,
        background_tasks=background_tasks,
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
        
        # Map playback_duration to duration_years (legacy support, default 30)
        playback_duration = metadata.get("playback_duration", "")
        duration_mapping = {
            "1_year": 1,
            "3_years": 3,
            "5_years": 5,
        }
        duration_years = duration_mapping.get(playback_duration, 30)
        
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
        
        # Parse duration_years (default: 30 years)
        duration_years_str = form.get("duration_years")
        try:
            duration_years = int(duration_years_str) if duration_years_str else 30
        except (ValueError, TypeError):
            duration_years = 30
        
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
    request: Request,
    company_id: int,
    project_id: int,
    data: dict = Depends(parse_ar_content_data),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
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
    if not getattr(current_user, 'is_super_admin', False) and getattr(current_user, 'company_id', None) is not None:
        if company_id != getattr(current_user, 'company_id', None):
            raise HTTPException(status_code=403, detail="Access denied to this company")
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
            db=db,
            background_tasks=background_tasks,
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
    request: Request,
    company_id: int,
    project_id: int,
    content_metadata: str = Form(...),
    image: UploadFile = File(...),
    video: UploadFile = File(...),
    description: str = Form(""),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
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
    
    # Map playback_duration to duration_years (legacy support, default 30)
    playback_duration = metadata.get("playback_duration", "")
    duration_mapping = {
        "1_year": 1,
        "3_years": 3,
        "5_years": 5,
    }
    duration_years = duration_mapping.get(playback_duration, 30)
    
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

    if not getattr(current_user, 'is_super_admin', False) and getattr(current_user, 'company_id', None) is not None:
        if company_id != getattr(current_user, 'company_id', None):
            raise HTTPException(status_code=403, detail="Access denied to this company")

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
        db=db,
        background_tasks=background_tasks,
    )




@router.get("/companies/{company_id}/projects/{project_id}/ar-content/{content_id}", response_model=ARContentWithLinks, tags=["AR Content"])
async def get_ar_content(
    request: Request,
    company_id: int,
    project_id: int,
    content_id: int,
    company: Company = Depends(require_company_access),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
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
    request: Request,
    company_id: int,
    project_id: int,
    content_id: int,
    update_data: ARContentUpdate,
    company: Company = Depends(require_company_access),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update mutable AR content metadata (never changes unique_id or QR code)."""
    # Validate company and project relationship
    await validate_company_project(company_id, project_id, db)

    # Get AR content
    ar_content = await get_ar_content_or_404(content_id, db)

    if not getattr(current_user, 'is_super_admin', False) and getattr(current_user, 'company_id', None) is not None:
        if ar_content.company_id != getattr(current_user, 'company_id', None):
            raise HTTPException(status_code=403, detail="Access denied to this AR content")
    
    # Verify it belongs to the specified company and project
    if ar_content.company_id != company_id or ar_content.project_id != project_id:
        raise HTTPException(status_code=404, detail="AR content not found in specified project")
    
    update_dict = update_data.model_dump(exclude_unset=True)

    # Allow moving content to another project within the same company.
    new_project_id = update_dict.get("project_id")
    if new_project_id is not None and new_project_id != ar_content.project_id:
        new_project = await db.get(Project, new_project_id)
        if not new_project:
            raise HTTPException(status_code=404, detail="Project not found")
        if new_project.company_id != ar_content.company_id:
            raise HTTPException(status_code=400, detail="Project does not belong to company")

    # Update only mutable fields
    for field, value in update_dict.items():
        setattr(ar_content, field, value)
    
    await db.commit()
    await db.refresh(ar_content)
    
    return ARContentSchema.model_validate(ar_content)


@router.patch("/companies/{company_id}/projects/{project_id}/ar-content/{content_id}/photo", response_model=ARContentSchema, tags=["AR Content"])
async def update_ar_content_photo(
    request: Request,
    company_id: int,
    project_id: int,
    content_id: int,
    photo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
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
    from app.core.storage_providers import get_provider_for_company
    storage_path = await get_ar_content_storage_path(ar_content, db)
    storage_path.mkdir(parents=True, exist_ok=True)
    provider = await get_provider_for_company(ar_content.company)

    # Save new photo
    photo_filename = f"photo{Path(photo.filename).suffix}"
    photo_path = storage_path / photo_filename
    await save_uploaded_file(photo, photo_path)

    # Resolve URL depending on provider
    if provider and hasattr(provider, 'save_file'):
        from app.core.yandex_disk_provider import YandexDiskStorageProvider
        if isinstance(provider, YandexDiskStorageProvider):
            from app.utils.slug_utils import generate_slug
            from app.utils.ar_content import sanitize_filename
            project_slug = generate_slug(ar_content.project.name) if ar_content.project else f"Project_{project_id}"
            order_folder = sanitize_filename(ar_content.order_number, max_length=50)
            yd_relative_prefix = f"{project_slug}/{order_folder}"
            yd_ref = await provider.save_file(str(photo_path), f"{yd_relative_prefix}/{photo_filename}")
            photo_url_val = yd_ref or provider.get_public_url(f"{yd_relative_prefix}/{photo_filename}")
        else:
            photo_url_val = build_public_url(photo_path, provider=provider)
    else:
        photo_url_val = build_public_url(photo_path)

    # Update database
    ar_content.photo_path = str(photo_path)
    ar_content.photo_url = photo_url_val

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
        ar_content.marker_url = photo_url_val
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
    request: Request,
    company_id: int,
    project_id: int,
    content_id: int,
    video: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
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
    from app.core.storage_providers import get_provider_for_company
    storage_path = await get_ar_content_storage_path(ar_content, db)
    storage_path.mkdir(parents=True, exist_ok=True)
    provider = await get_provider_for_company(ar_content.company)
    
    # Save new video
    video_filename = f"video{Path(video.filename).suffix}"
    video_path = storage_path / video_filename
    await save_uploaded_file(video, video_path)
    
    # Resolve URL depending on provider
    if provider and hasattr(provider, 'save_file'):
        from app.core.yandex_disk_provider import YandexDiskStorageProvider
        if isinstance(provider, YandexDiskStorageProvider):
            from app.utils.slug_utils import generate_slug
            from app.utils.ar_content import sanitize_filename
            project_slug = generate_slug(ar_content.project.name) if ar_content.project else f"Project_{project_id}"
            order_folder = sanitize_filename(ar_content.order_number, max_length=50)
            yd_relative_prefix = f"{project_slug}/{order_folder}"
            yd_ref = await provider.save_file(str(video_path), f"{yd_relative_prefix}/videos/{video_filename}")
            video_url_val = yd_ref or provider.get_public_url(f"{yd_relative_prefix}/videos/{video_filename}")
        else:
            video_url_val = build_public_url(video_path, provider=provider)
    else:
        video_url_val = build_public_url(video_path)
    
    # Update database
    ar_content.video_path = str(video_path)
    ar_content.video_url = video_url_val
    # Update preview URL as well
    if ar_content.active_video:
        ar_content.active_video.preview_url = video_url_val
    
    await db.commit()
    await db.refresh(ar_content)
    
    return ARContentSchema.model_validate(ar_content)


@router.delete("/companies/{company_id}/projects/{project_id}/ar-content/{content_id}", tags=["AR Content"])
async def delete_ar_content(
    request: Request,
    company_id: int,
    project_id: int,
    content_id: int,
    background_tasks: BackgroundTasks,
    company: Company = Depends(require_company_access),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete AR content and its storage folder."""
    # Validate company and project relationship
    await validate_company_project(company_id, project_id, db)

    # Get AR content with relations
    ar_content = await get_ar_content_or_404(content_id, db, load_relations=True)

    if not getattr(current_user, 'is_super_admin', False) and getattr(current_user, 'company_id', None) is not None:
        if ar_content.company_id != getattr(current_user, 'company_id', None):
            raise HTTPException(status_code=403, detail="Access denied to this AR content")
    
    # Verify it belongs to the specified company and project
    if ar_content.company_id != company_id or ar_content.project_id != project_id:
        raise HTTPException(status_code=404, detail="AR content not found in specified project")
    
    # Get storage path
    from app.utils.ar_content import get_ar_content_storage_path
    storage_path = await get_ar_content_storage_path(ar_content, db)
    
    # Clear the active_video_id reference to avoid circular dependency
    ar_content.active_video_id = None
    await db.commit()

    # Remove FK references from related tables before deleting
    from app.models.ar_view_session import ARViewSession
    from app.models.notification import Notification

    await db.execute(
        sa_delete(ARViewSession).where(ARViewSession.ar_content_id == content_id)
    )
    await db.execute(
        sa_update(Notification)
        .where(Notification.ar_content_id == content_id)
        .values(ar_content_id=None)
    )

    # Delete from database (cascades to related videos)
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
    request: Request,
    content_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
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

    if not getattr(current_user, 'is_super_admin', False) and getattr(current_user, 'company_id', None) is not None:
        if ar_content.company_id != getattr(current_user, 'company_id', None):
            raise HTTPException(status_code=403, detail="Access denied to this AR content")

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
    request: Request,
    content_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete AR content by ID without requiring company/project context"""
    # Get AR content with relations for building proper storage path
    ar_content = await get_ar_content_or_404(content_id, db, load_relations=True)

    if not getattr(current_user, 'is_super_admin', False) and getattr(current_user, 'company_id', None) is not None:
        if ar_content.company_id != getattr(current_user, 'company_id', None):
            raise HTTPException(status_code=403, detail="Access denied to this AR content")
    
    # Get storage path
    from app.utils.ar_content import get_ar_content_storage_path
    storage_path = await get_ar_content_storage_path(ar_content, db)
    
    # Clear the active_video_id reference to avoid circular dependency
    ar_content.active_video_id = None
    await db.commit()

    # Remove FK references from related tables before deleting
    from app.models.ar_view_session import ARViewSession
    from app.models.notification import Notification

    await db.execute(
        sa_delete(ARViewSession).where(ARViewSession.ar_content_id == content_id)
    )
    await db.execute(
        sa_update(Notification)
        .where(Notification.ar_content_id == content_id)
        .values(ar_content_id=None)
    )

    # Delete from database (cascades to related videos)
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


@router.get("/ar-content/{ar_content_id}/marker/validate", tags=["AR Content"])
async def validate_marker(
    request: Request,
    ar_content_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Validate AR marker (photo image) availability and basic quality for ARCore.
    No .mind file validation; marker = photo image.
    """
    ar_content = await db.get(ARContent, ar_content_id)
    if not ar_content:
        raise HTTPException(status_code=404, detail="AR content not found")

    if not getattr(current_user, 'is_super_admin', False) and getattr(current_user, 'company_id', None) is not None:
        if ar_content.company_id != getattr(current_user, 'company_id', None):
            raise HTTPException(status_code=403, detail="Access denied to this AR content")

    try:
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


@router.get("/ar-content/by-unique/{unique_id}", tags=["AR Content"])
async def get_ar_content_by_unique_id(
    request: Request,
    unique_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get AR content data by unique_id for the standalone AR viewer template.

    Returns marker_status and marker_url as JSON (the by-unique compatibility
    endpoint that templates/ar_viewer.html expects).
    """
    try:
        UUID(unique_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid unique_id format")

    stmt = select(ARContent).where(ARContent.unique_id == unique_id)
    result = await db.execute(stmt)
    ar_content = result.scalar_one_or_none()

    if not ar_content:
        raise HTTPException(status_code=404, detail="AR content not found")

    return {
        "id": ar_content.id,
        "unique_id": str(ar_content.unique_id),
        "order_number": ar_content.order_number,
        "status": ar_content.status,
        "marker_status": ar_content.marker_status,
        "marker_url": ar_content.marker_url,
        "photo_url": ar_content.photo_url,
        "thumbnail_url": ar_content.thumbnail_url,
        "video_url": ar_content.video_url,
    }


@router.post("/ar-content/photo/analyze", tags=["AR Content"])
async def analyze_photo_quality(
    request: Request,
    photo_file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Analyze uploaded photo for AR marker tracking quality.

    Accepts a photo via multipart upload, saves it to a temporary file,
    runs image quality analysis and returns
    metrics, quality level, and recommendations **without** persisting
    anything to the database.

    The temporary file is deleted after analysis.
    """
    import tempfile
    import os

    allowed_extensions = {"jpeg", "jpg", "png", "webp"}
    filename = photo_file.filename or ""
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=422,
            detail=f"Photo must be one of: {', '.join(sorted(allowed_extensions))}",
        )

    tmp_path: str | None = None
    try:
        suffix = f".{ext}" if ext else ".jpg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name
            contents = await photo_file.read()
            if len(contents) > 10 * 1024 * 1024:
                raise HTTPException(status_code=422, detail="File size must not exceed 10 MB")
            tmp.write(contents)

        import cv2
        from app.services.marker_service import image_quality_analyzer

        img = cv2.imread(tmp_path)
        if img is None:
            raise HTTPException(status_code=422, detail="Cannot decode image — upload a valid JPEG or PNG")

        height, width = img.shape[:2]
        metrics = image_quality_analyzer.analyze_image_quality(tmp_path)
        recommendations = image_quality_analyzer.build_image_recommendations(metrics)
        recognition_probability = metrics.get("recognition_probability")
        quality_level = image_quality_analyzer.get_quality_level(recognition_probability)

        logger.info(
            "photo_quality_analyzed",
            width=width,
            height=height,
            quality_level=quality_level,
            recognition_probability=recognition_probability,
        )

        return {
            "recognition_probability": recognition_probability,
            "quality_level": quality_level,
            "metrics": metrics,
            "recommendations": recommendations,
            "resolution": {"width": width, "height": height},
        }
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
