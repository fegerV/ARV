from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ProjectCreate(BaseModel):
    company_id: int = Field(..., description="Company ID the project belongs to")
    name: str = Field(..., min_length=1, max_length=255)
    slug: Optional[str] = Field(None, description="URL-friendly slug. Auto-generated if not provided.")
    folder_path: Optional[str] = None
    description: Optional[str] = None
    project_type: Optional[str] = None
    subscription_type: str = Field(default="monthly")
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    auto_renew: bool = Field(default=False)
    status: str = Field(default="active")
    notify_before_expiry_days: int = Field(default=7)
    tags: Optional[List[str]] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    folder_path: Optional[str] = None
    description: Optional[str] = None
    project_type: Optional[str] = None
    subscription_type: Optional[str] = None
    starts_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    auto_renew: Optional[bool] = None
    status: Optional[str] = None
    notify_before_expiry_days: Optional[int] = None
    tags: Optional[List[str]] = None


class ProjectResponse(BaseModel):
    id: int
    company_id: int
    name: str
    slug: str
    folder_path: Optional[str]
    description: Optional[str]
    project_type: Optional[str]
    subscription_type: str
    starts_at: Optional[datetime]
    expires_at: Optional[datetime]
    auto_renew: bool
    status: str
    notify_before_expiry_days: int
    tags: Optional[List[str]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    projects: List[ProjectResponse]