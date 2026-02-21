from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.enums import ProjectStatus


class ProjectCreate(BaseModel):
    """Schema for creating a new project"""

    model_config = ConfigDict(from_attributes=True)

    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    company_id: int = Field(..., description="Company ID")
    status: Optional[ProjectStatus] = Field(default=ProjectStatus.ACTIVE, description="Project status")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v is None:
            return ProjectStatus.ACTIVE
        return v


class ProjectUpdate(BaseModel):
    """Schema for updating an existing project"""

    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Project name")
    status: Optional[ProjectStatus] = Field(None, description="Project status")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v is not None and not isinstance(v, ProjectStatus):
            raise ValueError("Status must be a valid ProjectStatus enum value")
        return v


class ProjectResponse(BaseModel):
    """Schema for project response with computed properties"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    status: ProjectStatus
    company_id: int
    ar_content_count: int = Field(..., description="Number of AR content items for this project")
    created_at: datetime