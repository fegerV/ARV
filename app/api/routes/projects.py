from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.project import Project
from app.models.company import Company
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse

router = APIRouter()


@router.get("/companies/{company_id}/projects", response_model=List[ProjectResponse])
async def list_projects_for_company(company_id: int, db: AsyncSession = Depends(get_db)):
    # Validate parent company exists
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get projects for the company
    stmt = select(Project).where(Project.company_id == company_id)
    result = await db.execute(stmt)
    projects = result.scalars().all()
    
    return projects


@router.post("/companies/{company_id}/projects", response_model=ProjectResponse)
async def create_project_for_company(
    company_id: int, 
    project_data: ProjectCreate, 
    db: AsyncSession = Depends(get_db)
):
    # Validate parent company exists
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Create new project
    project = Project(
        company_id=company_id,
        name=project_data.name,
        description=project_data.description
    )
    
    db.add(project)
    await db.commit()
    await db.refresh(project)
    
    return project


@router.get("/companies/{company_id}/projects/{project_id}", response_model=ProjectResponse)
async def get_project_for_company(
    company_id: int, 
    project_id: int, 
    db: AsyncSession = Depends(get_db)
):
    # Validate parent company exists
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get project that belongs to this company
    stmt = select(Project).where(
        Project.id == project_id, 
        Project.company_id == company_id
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return project


@router.put("/companies/{company_id}/projects/{project_id}", response_model=ProjectResponse)
async def update_project_for_company(
    company_id: int, 
    project_id: int, 
    project_data: ProjectUpdate, 
    db: AsyncSession = Depends(get_db)
):
    # Validate parent company exists
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get project that belongs to this company
    stmt = select(Project).where(
        Project.id == project_id, 
        Project.company_id == company_id
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Update project fields
    if project_data.name is not None:
        project.name = project_data.name
    if project_data.description is not None:
        project.description = project_data.description
    
    await db.commit()
    await db.refresh(project)
    
    return project


@router.delete("/companies/{company_id}/projects/{project_id}")
async def delete_project_for_company(
    company_id: int, 
    project_id: int, 
    db: AsyncSession = Depends(get_db)
):
    # Validate parent company exists
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get project that belongs to this company
    stmt = select(Project).where(
        Project.id == project_id, 
        Project.company_id == company_id
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    await db.delete(project)
    await db.commit()
    
    return {"status": "deleted"}
