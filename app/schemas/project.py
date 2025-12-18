from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator
from app.enums import ProjectStatus


class ProjectCreate(BaseModel):
    """Schema for creating a new project"""
    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    company_id: int = Field(..., description="Company ID")
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


class ProjectResponse(BaseModel):
    """Schema for project response with computed properties"""
    id: str
    name: str
    status: ProjectStatus
    company_id: int
    ar_content_count: int = Field(..., description="Number of AR content items for this project")
    created_at: datetime

    class Config:
        from_attributes = True