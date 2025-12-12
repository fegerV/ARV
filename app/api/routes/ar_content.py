"""
AR Content API routes with Company → Project → AR Content hierarchy.
"""
from uuid import uuid4, UUID
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.core.config import settings
from app.core.database import get_db
from app.models.ar_content import ARContent
from app.models.project import Project
from app.models.company import Company
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

logger = structlog.get_logger()

router = APIRouter()


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


@router.post("/companies/{company_id}/projects/{project_id}/ar-content/new", response_model=ARContentCreateResponse, tags=["AR Content"])
async def create_ar_content(
    company_id: int,
    project_id: int,
    name: str = Form(...),
    content_metadata: Optional[str] = Form(None),  # JSON string
    image: UploadFile = File(...),
    video: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db)
):
    """Create new AR content with image and optional video."""
    # Validate company and project relationship
    await validate_company_project(company_id, project_id, db)
    
    # Generate unique identifier
    unique_id = uuid4()
    
    # Build storage path
    storage_path = build_ar_content_storage_path(company_id, project_id, unique_id)
    storage_path.mkdir(parents=True, exist_ok=True)
    
    # Save image
    image_filename = f"image{Path(image.filename).suffix}"
    image_path = storage_path / image_filename
    await save_uploaded_file(image, image_path)
    
    # Save video if provided
    video_path = None
    video_url = None
    if video:
        video_filename = f"video{Path(video.filename).suffix}"
        video_path = storage_path / video_filename
        await save_uploaded_file(video, video_path)
        video_url = build_public_url(video_path)
    
    # Generate QR code
    qr_code_url = await generate_qr_code(unique_id, storage_path)
    
    # Parse metadata if provided
    metadata = {}
    if content_metadata:
        import json
        try:
            metadata = json.loads(content_metadata)
        except json.JSONDecodeError:
            pass  # Keep empty dict if invalid JSON
    
    # Create database record
    ar_content = ARContent(
        company_id=company_id,
        project_id=project_id,
        unique_id=unique_id,
        name=name,
        content_metadata=metadata,
        image_path=str(image_path),
        image_url=build_public_url(image_path),
        video_path=str(video_path) if video_path else None,
        video_url=video_url,
        qr_code_path=str(storage_path / "qr_code.png"),
        qr_code_url=qr_code_url,
        is_active=True
    )
    
    db.add(ar_content)
    await db.commit()
    await db.refresh(ar_content)
    
    # TODO: Spawn thumbnail generation tasks
    # TODO: Spawn preview generation tasks
    
    return ARContentCreateResponse(
        id=ar_content.id,
        unique_id=ar_content.unique_id,
        unique_link=build_unique_link(ar_content.unique_id),
        image_url=ar_content.image_url,
        video_url=ar_content.video_url,
        qr_code_url=ar_content.qr_code_url,
        preview_url=ar_content.preview_url
    )


@router.get("/companies/{company_id}/projects/{project_id}/ar-content/{content_id}", response_model=ARContentWithLinks, tags=["AR Content"])
async def get_ar_content(
    company_id: int,
    project_id: int,
    content_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get full AR content metadata including all URLs."""
    # Validate company and project relationship
    await validate_company_project(company_id, project_id, db)
    
    # Get AR content
    ar_content = await get_ar_content_or_404(content_id, db)
    
    # Verify it belongs to the specified company and project
    if ar_content.company_id != company_id or ar_content.project_id != project_id:
        raise HTTPException(status_code=404, detail="AR content not found in specified project")
    
    # Add unique link
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
    
    # TODO: Recursively delete storage folder
    # For now, just log it
    logger.info(
        "ar_content_deleted",
        content_id=content_id,
        unique_id=str(ar_content.unique_id),
        storage_path=str(storage_path)
    )
    
    return {"message": "AR content deleted successfully"}