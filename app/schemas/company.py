from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime

class CompanyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    
    # Contacts
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    
    # Subscription
    subscription_tier: str = Field(default="basic")
    subscription_expires_at: Optional[datetime] = None
    
    # Quotas
    storage_quota_gb: int = Field(default=10, ge=1, le=1000)
    projects_limit: int = Field(default=50, ge=1, le=500)
    
    # Notes
    notes: Optional[str] = None


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    
    # Contacts
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    
    # Subscription
    subscription_tier: Optional[str] = None
    subscription_expires_at: Optional[datetime] = None
    
    # Quotas
    storage_quota_gb: Optional[int] = Field(None, ge=1, le=1000)
    projects_limit: Optional[int] = Field(None, ge=1, le=500)
    
    # Notes
    notes: Optional[str] = None
    
    # Status
    is_active: Optional[bool] = None


class Company(CompanyBase):
    id: int
    slug: str
    
    # Storage
    is_default: bool
    
    # Quotas
    storage_used_bytes: int
    
    # Status
    is_active: bool
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CompanyResponse(Company):
    projects_count: Optional[int] = None
    ar_content_count: Optional[int] = None