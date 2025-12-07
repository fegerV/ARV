from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.project import Project
from app.models.company import Company
from app.schemas.project import (
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse
)
from app.utils.slugify import slugify, generate_unique_slug
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new project."""
    try:
        # Validate company exists
        company = await db.get(Company, project.company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Company with ID {project.company_id} not found"
            )

        # Generate slug if not provided
        project_slug = project.slug
        if not project_slug:
            base_slug = slugify(project.name)
            
            # Check for existing slugs within the same company
            stmt = select(Project.slug).where(
                Project.slug.ilike(f"{base_slug}%"),
                Project.company_id == project.company_id
            )
            result = await db.execute(stmt)
            existing_slugs = [row[0] for row in result.fetchall()]
            project_slug = generate_unique_slug(project.name, existing_slugs)

        # Create project
        db_project = Project(
            company_id=project.company_id,
            name=project.name,
            slug=project_slug,
            folder_path=project.folder_path,
            description=project.description,
            project_type=project.project_type,
            subscription_type=project.subscription_type,
            starts_at=project.starts_at,
            expires_at=project.expires_at,
            auto_renew=1 if project.auto_renew else 0,
            status=project.status,
            notify_before_expiry_days=project.notify_before_expiry_days,
            tags=project.tags,
        )
        db.add(db_project)
        await db.commit()
        await db.refresh(db_project)

        logger.info("project_created", project_id=db_project.id, slug=project_slug)
        return db_project

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("project_creation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project"
        )


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    company_id: Optional[int] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List projects with optional filtering."""
    try:
        query = select(Project)
        
        if company_id:
            query = query.where(Project.company_id == company_id)
        
        if status:
            query = query.where(Project.status == status)
        
        query = query.order_by(Project.created_at.desc())
        result = await db.execute(query)
        projects = result.scalars().all()
        
        return projects

    except Exception as e:
        logger.error("project_list_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list projects"
        )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int, db: AsyncSession = Depends(get_db)):
    """Get project details by ID."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update project details."""
    try:
        # Get project
        db_project = await db.get(Project, project_id)
        if not db_project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        # Generate new slug if name is being updated
        update_data = project_update.dict(exclude_unset=True)
        if "name" in update_data and update_data["name"] != db_project.name:
            base_slug = slugify(update_data["name"])
            
            # Check for existing slugs within the same company
            stmt = select(Project.slug).where(
                Project.slug.ilike(f"{base_slug}%"),
                Project.company_id == db_project.company_id,
                Project.id != project_id
            )
            result = await db.execute(stmt)
            existing_slugs = [row[0] for row in result.fetchall()]
            update_data["slug"] = generate_unique_slug(update_data["name"], existing_slugs)

        # Handle boolean conversion
        if "auto_renew" in update_data:
            update_data["auto_renew"] = 1 if update_data["auto_renew"] else 0

        # Update fields
        for field, value in update_data.items():
            setattr(db_project, field, value)

        await db.commit()
        await db.refresh(db_project)

        logger.info("project_updated", project_id=project_id)
        return db_project

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("project_update_failed", error=str(e), project_id=project_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update project"
        )


@router.delete("/{project_id}")
async def delete_project(project_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a project."""
    try:
        project = await db.get(Project, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        await db.delete(project)
        await db.commit()

        logger.info("project_deleted", project_id=project_id)
        return {"status": "deleted", "id": project_id}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("project_deletion_failed", error=str(e), project_id=project_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete project"
        )


@router.post("/{project_id}/extend")
async def extend_project(
    project_id: int,
    days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """Extend project expiration by specified number of days."""
    try:
        project = await db.get(Project, project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )

        base = project.expires_at or datetime.utcnow()
        project.expires_at = base + timedelta(days=days)
        await db.commit()

        logger.info("project_extended", project_id=project_id, days=days)
        return {"expires_at": project.expires_at.isoformat()}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("project_extension_failed", error=str(e), project_id=project_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extend project"
        )


# Company-specific project endpoints
@router.get("/companies/{company_id}/projects", response_model=List[ProjectResponse])
async def get_company_projects(
    company_id: int,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all projects for a specific company."""
    try:
        # Validate company exists
        company = await db.get(Company, company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found"
            )

        query = select(Project).where(Project.company_id == company_id)
        
        if status:
            query = query.where(Project.status == status)
        
        query = query.order_by(Project.created_at.desc())
        result = await db.execute(query)
        projects = result.scalars().all()
        
        return projects

    except HTTPException:
        raise
    except Exception as e:
        logger.error("company_projects_failed", error=str(e), company_id=company_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get company projects"
        )


@router.post("/companies/{company_id}/projects", response_model=ProjectResponse)
async def create_project_for_company(
    company_id: int,
    project: ProjectCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a project for a specific company."""
    # Override the company_id with the one from the path
    project.company_id = company_id
    return await create_project(project, db)