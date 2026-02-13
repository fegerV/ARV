from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional
from datetime import datetime

from app.enums import CompanyStatus, StorageProviderType


class CompanyCreate(BaseModel):
    """Schema for creating a new company."""

    name: str = Field(..., min_length=1, max_length=255, description="Company name")
    contact_email: Optional[EmailStr] = Field(None, description="Contact email address")
    status: Optional[CompanyStatus] = Field(default=CompanyStatus.ACTIVE, description="Company status")
    storage_provider: StorageProviderType = Field(
        default=StorageProviderType.LOCAL,
        description="Storage backend: local or yandex_disk",
    )

    @validator('contact_email', pre=True)
    def empty_string_to_none(cls, v):
        """Convert empty string to None so Pydantic skips EmailStr validation."""
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @validator('status')
    def validate_status(cls, v):
        if v is None:
            return CompanyStatus.ACTIVE
        return v

    class Config:
        from_attributes = True


class CompanyUpdate(BaseModel):
    """Schema for updating an existing company."""

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Company name")
    contact_email: Optional[EmailStr] = Field(None, description="Contact email address")
    status: Optional[CompanyStatus] = Field(None, description="Company status")
    storage_provider: Optional[StorageProviderType] = Field(
        None,
        description="Storage backend: local or yandex_disk",
    )

    @validator('contact_email', pre=True)
    def empty_string_to_none(cls, v):
        """Convert empty string to None so Pydantic skips EmailStr validation."""
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @validator('status')
    def validate_status(cls, v):
        if v is not None and not isinstance(v, CompanyStatus):
            raise ValueError('Status must be a valid CompanyStatus enum value')
        return v

    class Config:
        from_attributes = True


class CompanyResponse(BaseModel):
    """Schema for company response with computed properties."""

    id: str
    name: str
    contact_email: Optional[str]
    status: CompanyStatus
    storage_provider: str = Field(default="local", description="Storage provider type")
    projects_count: int = Field(..., description="Number of projects for this company")
    ar_content_count: int = Field(..., description="Total AR content across all projects")
    created_at: datetime

    class Config:
        from_attributes = True