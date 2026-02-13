from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.enums import CompanyStatus


class CompanyCreate(BaseModel):
    """Schema for creating a new company"""
    name: str = Field(..., min_length=1, max_length=255, description="Company name")
    contact_email: Optional[EmailStr] = Field(None, description="Contact email address")
    status: Optional[CompanyStatus] = Field(default=CompanyStatus.ACTIVE, description="Company status")

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
    """Schema for updating an existing company"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Company name")
    contact_email: Optional[EmailStr] = Field(None, description="Contact email address")
    status: Optional[CompanyStatus] = Field(None, description="Company status")

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


class CompanyLinks(BaseModel):
    """HATEOAS links for company actions"""
    edit: str = Field(..., description="URL to edit the company")
    delete: str = Field(..., description="URL to delete the company")
    view_projects: str = Field(..., description="URL to view company's projects")
    view_content: str = Field(..., description="URL to view company's AR content")


class CompanyListItem(BaseModel):
    """Schema for company list item response"""
    id: str
    name: str
    contact_email: Optional[str]
    storage_provider: str = Field(default="Local", description="Storage provider (always 'Local')")
    status: CompanyStatus
    projects_count: int = Field(..., description="Number of projects for this company")
    created_at: datetime
    _links: CompanyLinks

    class Config:
        from_attributes = True


class CompanyDetail(BaseModel):
    """Schema for detailed company response"""
    id: str
    name: str
    contact_email: Optional[str]
    storage_provider: str = Field(default="Local", description="Storage provider (always 'Local')")
    status: CompanyStatus
    projects_count: int = Field(..., description="Number of projects for this company")
    ar_content_count: int = Field(..., description="Total AR content across all projects")
    created_at: datetime
    _links: CompanyLinks

    class Config:
        from_attributes = True


class PaginatedCompaniesResponse(BaseModel):
    """Schema for paginated companies list response"""
    items: List[CompanyListItem]
    total: int = Field(..., description="Total number of companies")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")