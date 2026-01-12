from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import structlog

from app.core.database import get_db
from app.models.project import Project
from app.models.company import Company
from app.models.ar_content import ARContent
from app.models.user import User
from app.schemas.project_api import (
    ProjectCreate, ProjectUpdate, ProjectListItem, ProjectDetail,
    ProjectLinks, PaginatedProjectsResponse
)
from app.api.routes.auth import get_current_active_user

router = APIRouter(tags=["projects"])


def _generate_project_links(project_id: int) -> ProjectLinks:
    """Generate HATEOAS links for a project"""
    return ProjectLinks(
        edit=f"/api/projects/{project_id}",
        delete=f"/api/projects/{project_id}",
        view_content=f"/api/projects/{project_id}/ar-content"
    )


# Эндпоинт для получения проектов по ID компании (для использования в формах)
@router.get("/api/projects/by-company/{company_id}")
async def get_projects_by_company(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get projects filtered by company ID - specifically for form dropdowns"""
    logger = structlog.get_logger()
    
    # Verify company exists
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get projects for the company
    query = select(Project).where(Project.company_id == company_id).order_by(Project.name)
    result = await db.execute(query)
    projects = result.scalars().all()
    
    # Format response for frontend
    projects_data = []
    for project in projects:
        # Count AR content for this project
        ar_content_count_query = select(func.count()).select_from(ARContent).where(ARContent.project_id == project.id)
        ar_content_count_result = await db.execute(ar_content_count_query)
        ar_content_count = ar_content_count_result.scalar()
        
        projects_data.append({
            "id": project.id,
            "name": project.name,
            "status": project.status,
            "company_id": project.company_id,
            "ar_content_count": ar_content_count,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "updated_at": project.updated_at.isoformat() if project.updated_at else None
        })
    
    logger.info("company_projects_fetched", company_id=company_id, count=len(projects_data))
    
    return {"projects": projects_data}


@router.get("/projects", response_model=PaginatedProjectsResponse)
async def list_projects(
   page: int = Query(default=1, ge=1, description="Page number"),
   page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
   company_id: Optional[int] = Query(default=None, description="Filter by company ID"),
   db: AsyncSession = Depends(get_db),
   current_user: User = Depends(get_current_active_user)
):
   """List projects with pagination and filtering"""
   logger = structlog.get_logger()
   
   # Build base query
   query = select(Project).join(Company)
   count_query = select(func.count()).select_from(Project).join(Company)
   
   # Apply filters
   where_conditions = []
   
   if company_id:
       where_conditions.append(Project.company_id == company_id)
   
   if where_conditions:
       query = query.where(*where_conditions)
       count_query = count_query.where(*where_conditions)
   
   # Get total count
   total_result = await db.execute(count_query)
   total = total_result.scalar()
   
   # Calculate pagination
   offset = (page - 1) * page_size
   total_pages = (total + page_size - 1) // page_size
   
   # Apply pagination and ordering
   query = query.order_by(Project.created_at.desc()).offset(offset).limit(page_size)
   
   # Execute query
   result = await db.execute(query)
   projects = result.scalars().all()
   
   # Build response items
   items = []
   for project in projects:
       # Load AR content count efficiently
       ar_content_count_query = select(func.count()).select_from(ARContent).where(ARContent.project_id == project.id)
       ar_content_count_result = await db.execute(ar_content_count_query)
       ar_content_count = ar_content_count_result.scalar()
       
       item = ProjectListItem(
           id=str(project.id),
           name=project.name,
           status=project.status,
           ar_content_count=ar_content_count,
           created_at=project.created_at,
           _links=_generate_project_links(project.id)
       )
       items.append(item)
   
   logger.info("projects_listed", total=total, page=page, page_size=page_size)
   
   return PaginatedProjectsResponse(
       items=items,
       total=total,
       page=page,
       page_size=page_size,
       total_pages=total_pages
   )


@router.get("/companies/{company_id}/projects", response_model=PaginatedProjectsResponse)
async def list_projects_for_company(
    company_id: int,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List projects for a specific company"""
    logger = structlog.get_logger()
    
    # Validate company exists
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Build query for company's projects
    query = select(Project).where(Project.company_id == company_id)
    count_query = select(func.count()).select_from(Project).where(Project.company_id == company_id)
    
    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Calculate pagination
    offset = (page - 1) * page_size
    total_pages = (total + page_size - 1) // page_size
    
    # Apply pagination and ordering
    query = query.order_by(Project.created_at.desc()).offset(offset).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    projects = result.scalars().all()
    
    # Build response items
    items = []
    for project in projects:
        # Load AR content count efficiently
        ar_content_count_query = select(func.count()).select_from(ARContent).where(ARContent.project_id == project.id)
        ar_content_count_result = await db.execute(ar_content_count_query)
        ar_content_count = ar_content_count_result.scalar()
        
        item = ProjectListItem(
            id=str(project.id),
            name=project.name,
            status=project.status,
            ar_content_count=ar_content_count,
            created_at=project.created_at,
            _links=_generate_project_links(project.id)
        )
        items.append(item)
    
    logger.info("company_projects_listed", company_id=company_id, total=total, page=page, page_size=page_size)
    
    return PaginatedProjectsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )
        

@router.post("/projects", response_model=ProjectDetail)
async def create_project_general(
   project_data: ProjectCreate,
   db: AsyncSession = Depends(get_db),
   current_user: User = Depends(get_current_active_user)
):
   """Create a new project"""
   logger = structlog.get_logger()
   
   # Validate company exists
   company = await db.get(Company, project_data.company_id)
   if not company:
       raise HTTPException(status_code=404, detail="Company not found")
   
   # Create project
   project = Project(
       company_id=project_data.company_id,
       name=project_data.name,
       status=project_data.status
   )
   
   db.add(project)
   await db.commit()
   await db.refresh(project)
   
   logger.info("project_created", project_id=project.id, company_id=project_data.company_id)
   
   return ProjectDetail(
       id=str(project.id),
       name=project.name,
       status=project.status,
       company_id=project.company_id,
       ar_content_count=0,
       created_at=project.created_at,
       _links=_generate_project_links(project.id)
   )


@router.get("/projects/{project_id}", response_model=ProjectDetail)
async def get_project_general(
   project_id: int,
   db: AsyncSession = Depends(get_db),
   current_user: User = Depends(get_current_active_user)
):
   """Get detailed project information"""
   logger = structlog.get_logger()
   
   # Get project
   project = await db.get(Project, project_id)
   if not project:
       raise HTTPException(status_code=404, detail="Project not found")
   
   # Get AR content count
   ar_content_count_query = select(func.count()).select_from(ARContent).where(ARContent.project_id == project.id)
   ar_content_count_result = await db.execute(ar_content_count_query)
   ar_content_count = ar_content_count_result.scalar()
   
   return ProjectDetail(
       id=str(project.id),
       name=project.name,
       status=project.status,
       company_id=project.company_id,
       ar_content_count=ar_content_count,
       created_at=project.created_at,
       _links=_generate_project_links(project_id)
   )


@router.put("/projects/{project_id}", response_model=ProjectDetail)
async def update_project_general(
   project_id: int,
   project_data: ProjectUpdate,
   db: AsyncSession = Depends(get_db),
   current_user: User = Depends(get_current_active_user)
):
   """Update project information"""
   logger = structlog.get_logger()
   
   # Get project
   project = await db.get(Project, project_id)
   if not project:
       raise HTTPException(status_code=404, detail="Project not found")
   
   # Update fields
   update_data = project_data.dict(exclude_unset=True)
   for field, value in update_data.items():
       setattr(project, field, value)
   
   await db.commit()
   await db.refresh(project)
   
   # Get AR content count for response
   ar_content_count_query = select(func.count()).select_from(ARContent).where(ARContent.project_id == project.id)
   ar_content_count_result = await db.execute(ar_content_count_query)
   ar_content_count = ar_content_count_result.scalar()
   
   logger.info("project_updated", project_id=project.id)
   
   return ProjectDetail(
       id=str(project.id),
       name=project.name,
       status=project.status,
       company_id=project.company_id,
       ar_content_count=ar_content_count,
       created_at=project.created_at,
       _links=_generate_project_links(project_id)
   )


@router.delete("/projects/{project_id}")
async def delete_project_general(
   project_id: int,
   db: AsyncSession = Depends(get_db),
   current_user: User = Depends(get_current_active_user)
):
   """Delete a project (with dependency checks)"""
   logger = structlog.get_logger()
   
   # Get project
   project = await db.get(Project, project_id)
   if not project:
       raise HTTPException(status_code=404, detail="Project not found")
   
   # Check for dependencies
   ar_content_count_query = select(func.count()).select_from(ARContent).where(ARContent.project_id == project.id)
   ar_content_count_result = await db.execute(ar_content_count_query)
   ar_content_count = ar_content_count_result.scalar()
   
   if ar_content_count > 0:
       raise HTTPException(
           status_code=400,
           detail=f"Cannot delete project with {ar_content_count} AR content items. Delete content first."
       )
   
   # Delete project
   await db.delete(project)
   await db.commit()
   
   logger.info("project_deleted", project_id=project_id, name=project.name)
   
   return {"status": "deleted"}


@router.post("/companies/{company_id}/projects", response_model=ProjectDetail)
async def create_project(
    company_id: int,
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new project within a specific company"""
    logger = structlog.get_logger()
    
    # Validate company exists
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Create project
    project = Project(
        company_id=company_id,
        name=project_data.name,
        status=project_data.status
    )
    
    db.add(project)
    await db.commit()
    await db.refresh(project)
    
    logger.info("project_created", project_id=project.id, company_id=company_id)
    
    return ProjectDetail(
        id=str(project.id),
        name=project.name,
        status=project.status,
        company_id=project.company_id,
        ar_content_count=0,
        created_at=project.created_at,
        _links=_generate_project_links(project.id)
    )


@router.get("/companies/{company_id}/projects/{project_id}", response_model=ProjectDetail)
async def get_project(
    company_id: int,
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get detailed project information within a specific company"""
    logger = structlog.get_logger()
    
    # Get project
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Verify project belongs to company
    if project.company_id != company_id:
        raise HTTPException(status_code=404, detail="Project does not belong to specified company")
    
    # Get AR content count
    ar_content_count_query = select(func.count()).select_from(ARContent).where(ARContent.project_id == project.id)
    ar_content_count_result = await db.execute(ar_content_count_query)
    ar_content_count = ar_content_count_result.scalar()
    
    return ProjectDetail(
        id=str(project.id),
        name=project.name,
        status=project.status,
        company_id=project.company_id,
        ar_content_count=ar_content_count,
        created_at=project.created_at,
        _links=_generate_project_links(project_id)
    )


@router.put("/companies/{company_id}/projects/{project_id}", response_model=ProjectDetail)
async def update_project(
    company_id: int,
    project_id: int,
    project_data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update project information within a specific company"""
    logger = structlog.get_logger()
    
    # Get project
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Verify project belongs to company
    if project.company_id != company_id:
        raise HTTPException(status_code=404, detail="Project does not belong to specified company")
    
    # Update fields
    update_data = project_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    
    await db.commit()
    await db.refresh(project)
    
    # Get AR content count for response
    ar_content_count_query = select(func.count()).select_from(ARContent).where(ARContent.project_id == project.id)
    ar_content_count_result = await db.execute(ar_content_count_query)
    ar_content_count = ar_content_count_result.scalar()
    
    logger.info("project_updated", project_id=project.id)
    
    return ProjectDetail(
        id=str(project.id),
        name=project.name,
        status=project.status,
        company_id=project.company_id,
        ar_content_count=ar_content_count,
        created_at=project.created_at,
        _links=_generate_project_links(project_id)
    )


@router.delete("/companies/{company_id}/projects/{project_id}")
async def delete_project(
    company_id: int,
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a project (with dependency checks) within a specific company"""
    logger = structlog.get_logger()
    
    # Get project
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Verify project belongs to company
    if project.company_id != company_id:
        raise HTTPException(status_code=404, detail="Project does not belong to specified company")
    
    # Check for dependencies
    ar_content_count_query = select(func.count()).select_from(ARContent).where(ARContent.project_id == project.id)
    ar_content_count_result = await db.execute(ar_content_count_query)
    ar_content_count = ar_content_count_result.scalar()
    
    if ar_content_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete project with {ar_content_count} AR content items. Delete content first."
        )
    
    # Delete project
    await db.delete(project)
    await db.commit()
    
    logger.info("project_deleted", project_id=project_id, name=project.name)
    
    return {"status": "deleted"}
