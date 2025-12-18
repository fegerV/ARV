from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.enums import ProjectStatus


class ProjectCreate(BaseModel):
    """Schema for creating a new project"""
    company_id: int = Field(..., description="Company ID")
    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    status: Optional[ProjectStatus] = Field(default=ProjectStatus.ACTIVE, description="Project status")

    @validator('status')
    def validate_status(cls, v):
        if v is None:
            return ProjectStatus.ACTIVE
        return v

    class Config:
        from_attributes = True


class ProjectUpdate(BaseModel):
    """Schema for updating an existing project"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Project name")
    status: Optional[ProjectStatus] = Field(None, description="Project status")

    @validator('status')
    def validate_status(cls, v):
        if v is not None and not isinstance(v, ProjectStatus):
            raise ValueError('Status must be a valid ProjectStatus enum value')
        return v

    class Config:
        from_attributes = True


class ProjectLinks(BaseModel):
    """HATEOAS links for project actions"""
    edit: str = Field(..., description="URL to edit the project")
    delete: str = Field(..., description="URL to delete the project")
    view_content: str = Field(..., description="URL to view project's AR content")


class ProjectListItem(BaseModel):
    """Schema for project list item response"""
    id: str
    name: str
    status: ProjectStatus
    ar_content_count: int = Field(..., description="Number of AR content items for this project")
    created_at: datetime
    _links: ProjectLinks

    class Config:
        from_attributes = True


class ProjectDetail(BaseModel):
    """Schema for detailed project response"""
    id: str
    name: str
    status: ProjectStatus
    company_id: int
    ar_content_count: int = Field(..., description="Number of AR content items for this project")
    created_at: datetime
    _links: ProjectLinks

    class Config:
        from_attributes = True


class PaginatedProjectsResponse(BaseModel):
    """Schema for paginated projects list response"""
    items: List[ProjectListItem]
    total: int = Field(..., description="Total number of projects")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")