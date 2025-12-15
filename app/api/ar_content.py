"""
AR Content API endpoints for managing AR content with flat URL structure.
"""
import uuid
import re
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timedelta

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
import structlog

from app.core.config import settings
from app.core.database import get_db
from app.models.ar_content import ARContent
from app.models.video import Video
from app.models.project import Project
from app.models.company import Company
from app.models.ar_view_session import ARViewSession
from app.schemas.ar_content_api import (
    ARContentListResponse,
    ARContentDetailResponse,
    ARContentCreateRequest,
    ARContentUpdateRequest,
    VideoListResponse,
    VideoResponse,
    ARContentCreateResponse
)
from app.utils.ar_content import (
    build_ar_content_storage_path,
    build_public_url,
    build_unique_link,
    generate_qr_code,
    save_uploaded_file
)
from app.core.storage import get_storage_provider_instance

logger = structlog.get_logger()

router = APIRouter()


def _set_deprecated_canonical(response: Response, canonical_path: str) -> None:
    """Mark endpoint as deprecated and provide canonical Link header.

    canonical_path must be an API path (e.g. /api/companies/1/projects/2/ar-content/3).
    """
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = f"<{canonical_path}>; rel=\"canonical\""


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_file_type(filename: str, allowed_types: List[str]) -> bool:
    """Validate file type."""
    file_extension = Path(filename).suffix.lower()
    return file_extension in allowed_types


async def generate_order_number(db: AsyncSession) -> str:
    """Generate unique order number with format: AR-YYYYMMDD-XXXX"""
    today = datetime.now().strftime("%Y%m%d")
    
    # Count existing orders for today
    stmt = select(func.coalesce(func.count(), 0)).where(
        ARContent.order_number.like(f"AR-{today}-%")
    )
    result = await db.execute(stmt)
    count = result.scalar() or 0
    
    # Generate sequential number
    sequence = str(count + 1).zfill(4)
    return f"AR-{today}-{sequence}"


@router.get("/ar-content", response_model=ARContentListResponse, tags=["AR Content"])
async def list_ar_content(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    company_id: Optional[int] = Query(None, description="Filter by company ID"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by customer name or email"),
    sort_by: Optional[str] = Query("created_at", description="Sort field"),
    sort_order: Optional[str] = Query("desc", description="Sort order: asc or desc"),
    db: AsyncSession = Depends(get_db),
    response: Response = None,
):
    """LEGACY: Get list of AR content with pagination and filtering.

    Canonical API is hierarchical: /api/companies/{company_id}/projects/{project_id}/ar-content
    This endpoint remains for admin aggregation screens.
    """
    if response is not None:
        _set_deprecated_canonical(response, "/api/companies/{company_id}/projects/{project_id}/ar-content")
    
    # Build base query with joins
    base_query = (
        select(ARContent, Company, Project)
        .join(Project, ARContent.project_id == Project.id)
        .join(Company, Project.company_id == Company.id)
    )
    
    # Count query
    count_query = (
        select(func.count(ARContent.id))
        .join(Project, ARContent.project_id == Project.id)
        .join(Company, Project.company_id == Company.id)
    )
    
    # Apply filters
    filters = []
    
    if company_id:
        filters.append(Company.id == company_id)
    
    if project_id:
        filters.append(Project.id == project_id)
    
    if status:
        filters.append(ARContent.status == status)
    
    if search:
        search_filter = or_(
            ARContent.customer_name.ilike(f"%{search}%"),
            ARContent.customer_email.ilike(f"%{search}%")
        )
        filters.append(search_filter)
    
    if filters:
        base_query = base_query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))
    
    # Apply sorting
    sort_column = getattr(ARContent, sort_by, ARContent.created_at)
    if sort_order.lower() == "desc":
        base_query = base_query.order_by(sort_column.desc())
    else:
        base_query = base_query.order_by(sort_column.asc())
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply pagination
    offset = (page - 1) * page_size
    base_query = base_query.offset(offset).limit(page_size)
    
    # Execute query
    result = await db.execute(base_query)
    rows = result.all()

    since_30d = datetime.utcnow() - timedelta(days=30)
    content_ids = [ar_content.id for ar_content, _, _ in rows]
    views_30d_by_content: dict = {}
    if content_ids:
        views_stmt = (
            select(ARViewSession.ar_content_id, func.count().label("views_30d"))
            .where(ARViewSession.created_at >= since_30d)
            .where(ARViewSession.ar_content_id.in_(content_ids))
            .group_by(ARViewSession.ar_content_id)
        )
        views_res = await db.execute(views_stmt)
        views_30d_by_content = {row[0]: row[1] for row in views_res.all()}
    
    # Build response items
    items = []
    for ar_content, company, project in rows:
        active_video_url = getattr(ar_content, 'video_url', None)
        active_video_title = None
        if ar_content.active_video_id:
            video_stmt = select(Video).where(Video.id == ar_content.active_video_id)
            video_result = await db.execute(video_stmt)
            active_video = video_result.scalar_one_or_none()
            if active_video:
                active_video_title = active_video.filename
        
        photo_url = getattr(ar_content, 'photo_url', None)
        thumbnail_url = photo_url
        qr_code_url = getattr(ar_content, 'qr_code_url', None)
        has_qr_code = bool(qr_code_url)
        public_link = ar_content.public_link
        public_url = f"{settings.PUBLIC_URL.rstrip('/')}{public_link}"
        views_30_days = views_30d_by_content.get(ar_content.id, 0)
        
        item = {
            "id": str(ar_content.id),
            "order_number": ar_content.order_number,
            "company_name": company.name,
            "company_id": str(company.id),
            "project_id": str(project.id),
            "project_name": project.name,
            "created_at": ar_content.created_at.isoformat(),
            "status": ar_content.status,
            "customer_name": ar_content.customer_name,
            "customer_phone": ar_content.customer_phone,
            "customer_email": ar_content.customer_email,
            "photo_url": photo_url,
            "thumbnail_url": thumbnail_url,
            "active_video_url": active_video_url,
            "active_video_title": active_video_title,
            "views_count": ar_content.views_count,
            "views_30_days": views_30_days,
            "public_link": public_link,
            "public_url": public_url,
            "has_qr_code": has_qr_code,
            "qr_code_url": qr_code_url,
            "_links": {
                "view": f"/api/ar-content/{ar_content.id}",
                "edit": f"/api/ar-content/{ar_content.id}",
                "delete": f"/api/ar-content/{ar_content.id}"
            }
        }
        items.append(item)
    
    return ARContentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/ar-content/by-unique/{unique_id}", tags=["AR Content"])
async def get_ar_content_by_unique_id(unique_id: str, db: AsyncSession = Depends(get_db)):
    """Public-viewer helper endpoint: resolve AR content by unique_id."""
    stmt = (
        select(ARContent)
        .options(selectinload(ARContent.project).selectinload(Project.company))
        .where(ARContent.unique_id == unique_id)
    )
    res = await db.execute(stmt)
    ar_content = res.scalar_one_or_none()

    if not ar_content or not ar_content.is_active:
        raise HTTPException(status_code=404, detail="AR content not found")

    # Marker: currently modeled as API endpoints (placeholder until stored fields exist)
    marker_url = f"/api/ar-content/{ar_content.id}/marker"
    marker_preview_url = f"/api/ar-content/{ar_content.id}/marker/preview"
    marker_status = "ready"  # minimal: assume ready if content exists

    # Active video: prefer active_video_id, else legacy video_url
    active_video_url = ar_content.video_url
    if ar_content.active_video_id:
        vres = await db.execute(select(Video).where(Video.id == ar_content.active_video_id))
        v = vres.scalar_one_or_none()
        if v and v.video_url:
            active_video_url = v.video_url

    return {
        "id": str(ar_content.id),
        "unique_id": str(ar_content.unique_id),
        "order_number": ar_content.order_number,
        "photo_url": ar_content.photo_url,
        "marker_status": marker_status,
        "marker_url": marker_url,
        "marker_preview_url": marker_preview_url,
        "active_video_url": active_video_url,
    }


@router.get("/ar-content/{content_id}/marker", tags=["AR Content"])
async def get_ar_content_marker(content_id: str):
    """Return MindAR marker (.mind) file for public viewer.

    Minimal implementation: looks for a local file under MEDIA_ROOT/markers/{content_id}/targets.mind.
    """
    marker_path = Path(settings.MEDIA_ROOT) / "markers" / str(content_id) / "targets.mind"
    if not marker_path.exists():
        raise HTTPException(status_code=404, detail="Marker not found")

    return FileResponse(
        path=str(marker_path),
        media_type="application/octet-stream",
        filename="targets.mind",
    )


@router.get("/ar-content/{content_id}/marker/preview", tags=["AR Content"])
async def get_ar_content_marker_preview(content_id: str):
    """Marker preview placeholder.

    Keeping endpoint for UI/viewer compatibility.
    """
    raise HTTPException(status_code=404, detail="Marker preview not implemented")


@router.post("/ar-content", response_model=ARContentCreateResponse, tags=["AR Content"])
async def create_ar_content(
    company_id: int = Form(...),
    project_id: str = Form(...),
    customer_name: Optional[str] = Form(None),
    customer_phone: Optional[str] = Form(None),
    customer_email: str = Form(None),
    duration_years: int = Form(1),
    photo_file: UploadFile = File(...),
    video_file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    response: Response = None,
):
    """LEGACY: Create new AR content with photo and optional video.

    Canonical API: POST /api/companies/{company_id}/projects/{project_id}/ar-content/new
    """
    if response is not None:
        _set_deprecated_canonical(response, f"/api/companies/{company_id}/projects/{project_id}/ar-content/new")
    
    # Validate duration years
    if duration_years not in [1, 3, 5]:
        raise HTTPException(status_code=400, detail="duration_years must be 1, 3, or 5")
    
    # Validate email if provided
    if customer_email and not validate_email(customer_email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    # Validate file types
    if not validate_file_type(photo_file.filename, ['.jpg', '.jpeg', '.png']):
        raise HTTPException(status_code=400, detail="Photo must be JPG or PNG")
    
    if video_file and not validate_file_type(video_file.filename, ['.mp4']):
        raise HTTPException(status_code=400, detail="Video must be MP4")
    
    # Validate company and project exist
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.company_id != company_id:
        raise HTTPException(status_code=400, detail="Project does not belong to company")
    
    # Generate unique identifiers
    unique_id = uuid.uuid4()
    order_number = await generate_order_number(db)
    
    # Build storage path
    storage_path = build_ar_content_storage_path(company_id, project_id, unique_id)
    storage_path.mkdir(parents=True, exist_ok=True)
    
    # Save photo
    photo_filename = f"photo{Path(photo_file.filename).suffix}"
    photo_path = storage_path / photo_filename
    await save_uploaded_file(photo_file, photo_path)
    photo_url = build_public_url(photo_path)
    
    # Save video if provided
    video_path = None
    video_url = None
    if video_file:
        video_filename = f"video{Path(video_file.filename).suffix}"
        video_path = storage_path / video_filename
        await save_uploaded_file(video_file, video_path)
        video_url = build_public_url(video_path)
    
    # Generate QR code
    qr_code_url = await generate_qr_code(unique_id, storage_path)
    
    # Create AR content record
    ar_content = ARContent(
        project_id=project_id,
        unique_id=unique_id,
        order_number=order_number,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_email=customer_email,
        duration_years=duration_years,
        photo_path=str(photo_path),
        photo_url=photo_url,
        video_path=str(video_path) if video_path else None,
        video_url=video_url,
        qr_code_path=str(storage_path / "qr_code.png"),
        qr_code_url=qr_code_url,
        status="pending"
    )
    
    db.add(ar_content)
    await db.commit()
    await db.refresh(ar_content)
    
    # TODO: Generate NFT marker
    marker_url = f"/api/ar-content/{ar_content.id}/marker"
    
    return ARContentCreateResponse(
        id=str(ar_content.id),
        order_number=ar_content.order_number,
        public_link=ar_content.public_link,
        qr_code_url=qr_code_url,
        marker_url=marker_url,
        photo_url=photo_url,
        video_url=video_url
    )


@router.get("/ar-content/{content_id}", response_model=ARContentDetailResponse, tags=["AR Content"])
async def get_ar_content_details(content_id: str, db: AsyncSession = Depends(get_db), response: Response = None):
    """LEGACY: Get detailed information about AR content.

    Canonical API: GET /api/companies/{company_id}/projects/{project_id}/ar-content/{content_id}
    """
    
    # Get AR content with relationships
    stmt = (
        select(ARContent, Company, Project)
        .join(Project, ARContent.project_id == Project.id)
        .join(Company, Project.company_id == Company.id)
        .where(ARContent.id == content_id)
        .options(selectinload(ARContent.videos))
    )
    
    result = await db.execute(stmt)
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="AR content not found")
    
    ar_content, company, project = row

    if response is not None:
        _set_deprecated_canonical(response, f"/api/companies/{company.id}/projects/{project.id}/ar-content/{ar_content.id}")

    since_30d = datetime.utcnow() - timedelta(days=30)
    views_stmt = select(func.count()).select_from(ARViewSession).where(
        ARViewSession.ar_content_id == ar_content.id,
        ARViewSession.created_at >= since_30d,
    )
    views_res = await db.execute(views_stmt)
    views_30_days = views_res.scalar() or 0
    
    # Get videos
    videos = []
    active_video_title = None
    for video in ar_content.videos:
        if str(video.id) == str(ar_content.active_video_id):
            active_video_title = video.filename
        video_item = {
            "id": str(video.id),
            "filename": video.filename,
            "uploaded_at": video.created_at.isoformat(),
            "is_active": str(video.id) == str(ar_content.active_video_id),
            "thumbnail_url": f"/storage/thumbnails/{video.id}.jpg",
            "duration": video.duration,
            "size": video.size,
            "_links": {
                "set_active": f"/api/ar-content/{content_id}/videos/{video.id}/set-active",
                "download": f"/api/ar-content/{content_id}/videos/{video.id}/download",
                "delete": f"/api/ar-content/{content_id}/videos/{video.id}"
            }
        }
        videos.append(video_item)
    
    # Get stats (placeholder for now)
    stats = {
        "views": ar_content.views_count,
        "last_viewed": None  # TODO: Implement view tracking
    }
    
    return ARContentDetailResponse(
        id=str(ar_content.id),
        order_number=ar_content.order_number,
        company_name=company.name,
        company_id=str(company.id),
        project_id=str(project.id),
        project_name=project.name,
        created_at=ar_content.created_at.isoformat(),
        status=ar_content.status,
        customer_name=ar_content.customer_name,
        customer_phone=ar_content.customer_phone,
        customer_email=ar_content.customer_email,
        duration_years=ar_content.duration_years,
        photo_url=getattr(ar_content, 'photo_url', None),
        thumbnail_url=getattr(ar_content, 'photo_url', None),
        active_video_url=getattr(ar_content, 'video_url', None),
        active_video_title=active_video_title,
        views_count=ar_content.views_count,
        views_30_days=views_30_days,
        public_link=ar_content.public_link,
        public_url=f"{settings.PUBLIC_URL.rstrip('/')}{ar_content.public_link}",
        has_qr_code=bool(getattr(ar_content, 'qr_code_url', None)),
        qr_code_url=getattr(ar_content, 'qr_code_url', None),
        marker_url=f"/api/ar-content/{content_id}/marker",
        marker_preview_url=f"/api/ar-content/{content_id}/marker/preview",
        videos=videos,
        stats=stats,
        _links={
            "view": f"/api/ar-content/{content_id}",
            "edit": f"/api/ar-content/{content_id}",
            "delete": f"/api/ar-content/{content_id}",
            "videos": f"/api/ar-content/{content_id}/videos"
        }
    )


@router.put("/ar-content/{content_id}", response_model=ARContentDetailResponse, tags=["AR Content"])
async def update_ar_content(
    content_id: str,
    update_data: ARContentUpdateRequest,
    db: AsyncSession = Depends(get_db),
    response: Response = None,
):
    """LEGACY: Update AR content details.

    Canonical API: PUT /api/companies/{company_id}/projects/{project_id}/ar-content/{content_id}
    """
    
    ar_content = await db.get(ARContent, content_id)
    if not ar_content:
        raise HTTPException(status_code=404, detail="AR content not found")

    # Compute canonical path
    project = await db.get(Project, ar_content.project_id)
    if project:
        if response is not None:
            _set_deprecated_canonical(response, f"/api/companies/{project.company_id}/projects/{project.id}/ar-content/{ar_content.id}")
    
    # Validate email if provided
    if update_data.customer_email and not validate_email(update_data.customer_email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(ar_content, field, value)
    
    await db.commit()
    await db.refresh(ar_content)
    
    # Return updated details
    return await get_ar_content_details(content_id, db)


@router.get("/ar-content/{content_id}/videos", response_model=VideoListResponse, tags=["AR Content"])
async def list_ar_content_videos(content_id: str, db: AsyncSession = Depends(get_db)):
    """Get list of videos for AR content."""
    
    ar_content = await db.get(ARContent, content_id)
    if not ar_content:
        raise HTTPException(status_code=404, detail="AR content not found")
    
    stmt = select(Video).where(Video.ar_content_id == content_id).order_by(Video.created_at.desc())
    result = await db.execute(stmt)
    videos = result.scalars().all()
    
    video_items = []
    for video in videos:
        item = {
            "id": str(video.id),
            "filename": video.filename,
            "uploaded_at": video.created_at.isoformat(),
            "is_active": str(video.id) == str(ar_content.active_video_id),
            "thumbnail_url": f"/storage/thumbnails/{video.id}.jpg",
            "duration": video.duration,
            "size": video.size,
            "status": video.video_status,
            "_links": {
                "set_active": f"/api/ar-content/{content_id}/videos/{video.id}/set-active",
                "download": f"/api/ar-content/{content_id}/videos/{video.id}/download",
                "delete": f"/api/ar-content/{content_id}/videos/{video.id}"
            }
        }
        video_items.append(item)
    
    return VideoListResponse(
        items=video_items,
        total=len(video_items)
    )


@router.post("/ar-content/{content_id}/videos", response_model=VideoResponse, tags=["AR Content"])
async def upload_ar_content_video(
    content_id: str,
    video_file: UploadFile = File(...),
    set_as_active: bool = Form(False),
    db: AsyncSession = Depends(get_db)
):
    """Upload new video for AR content."""
    
    # Validate file type
    if not validate_file_type(video_file.filename, ['.mp4']):
        raise HTTPException(status_code=400, detail="Video must be MP4")
    
    ar_content = await db.get(ARContent, content_id)
    if not ar_content:
        raise HTTPException(status_code=404, detail="AR content not found")
    
    # Get project and company for storage path
    project = await db.get(Project, ar_content.project_id)
    company = await db.get(Company, project.company_id)

    if response is not None:
        _set_deprecated_canonical(response, f"/api/companies/{company.id}/projects/{project.id}/ar-content/{ar_content.id}")
    
    # Build storage path
    storage_path = build_ar_content_storage_path(company.id, str(project.id), ar_content.unique_id)
    
    # Save video
    video_filename = f"video_{uuid.uuid4()}{Path(video_file.filename).suffix}"
    video_path = storage_path / video_filename
    await save_uploaded_file(video_file, video_path)
    
    # Create video record
    video = Video(
        ar_content_id=content_id,
        filename=video_filename,
        video_status="uploaded"
    )
    
    db.add(video)
    await db.commit()
    await db.refresh(video)
    
    # Set as active if requested
    if set_as_active:
        ar_content.active_video_id = video.id
        await db.commit()
    
    # TODO: Schedule thumbnail generation and video processing
    
    return VideoResponse(
        id=str(video.id),
        ar_content_id=content_id,
        filename=video.filename,
        duration=video.duration,
        size=video.size,
        status=video.video_status,
        uploaded_at=video.created_at.isoformat(),
        is_active=str(video.id) == str(ar_content.active_video_id),
        thumbnail_url=f"/storage/thumbnails/{video.id}.jpg",
        _links={
            "set_active": f"/api/ar-content/{content_id}/videos/{video.id}/set-active",
            "download": f"/api/ar-content/{content_id}/videos/{video.id}/download",
            "delete": f"/api/ar-content/{content_id}/videos/{video.id}"
        }
    )


@router.put("/ar-content/{content_id}/videos/{video_id}/set-active", tags=["AR Content"])
async def set_active_video(content_id: str, video_id: str, db: AsyncSession = Depends(get_db)):
    """Set video as active for AR content."""
    
    ar_content = await db.get(ARContent, content_id)
    if not ar_content:
        raise HTTPException(status_code=404, detail="AR content not found")
    
    video = await db.get(Video, video_id)
    if not video or video.ar_content_id != content_id:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Set as active
    ar_content.active_video_id = video.id
    await db.commit()
    
    return {"message": "Video set as active successfully"}


@router.delete("/ar-content/{content_id}/videos/{video_id}", tags=["AR Content"])
async def delete_ar_content_video(content_id: str, video_id: str, db: AsyncSession = Depends(get_db)):
    """Delete video from AR content."""
    
    ar_content = await db.get(ARContent, content_id)
    if not ar_content:
        raise HTTPException(status_code=404, detail="AR content not found")
    
    video = await db.get(Video, video_id)
    if not video or video.ar_content_id != content_id:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Check if it's the last video
    stmt = select(func.count(Video.id)).where(Video.ar_content_id == content_id)
    result = await db.execute(stmt)
    video_count = result.scalar()
    
    if video_count <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last video")
    
    # Clear active video if this is the active one
    if str(ar_content.active_video_id) == video_id:
        # Get another video to set as active
        other_stmt = select(Video).where(
            and_(Video.ar_content_id == content_id, Video.id != video_id)
        ).limit(1)
        other_result = await db.execute(other_stmt)
        other_video = other_result.scalar_one_or_none()
        
        if other_video:
            ar_content.active_video_id = other_video.id
        else:
            ar_content.active_video_id = None
    
    # Delete video
    await db.delete(video)
    await db.commit()
    
    # TODO: Delete video file from storage
    
    return {"message": "Video deleted successfully"}


@router.delete("/ar-content/{content_id}", tags=["AR Content"])
async def delete_ar_content(content_id: str, db: AsyncSession = Depends(get_db), response: Response = None):
    """LEGACY: Delete AR content and all associated data.

    Canonical API: DELETE /api/companies/{company_id}/projects/{project_id}/ar-content/{content_id}
    """
    
    ar_content = await db.get(ARContent, content_id)
    if not ar_content:
        raise HTTPException(status_code=404, detail="AR content not found")
    
    # Get project and company for storage path
    project = await db.get(Project, ar_content.project_id)
    company = await db.get(Company, project.company_id)
    
    # Build storage path for cleanup
    storage_path = build_ar_content_storage_path(company.id, str(project.id), ar_content.unique_id)
    
    # Delete from database (cascade will delete videos)
    await db.delete(ar_content)
    await db.commit()
    
    # TODO: Delete storage folder
    
    logger.info(
        "ar_content_deleted",
        content_id=content_id,
        order_number=ar_content.order_number,
        storage_path=str(storage_path)
    )
    
    return {"message": "AR content deleted successfully"}