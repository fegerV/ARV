from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID
from enum import Enum


class ARContentStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PROCESSING = "processing"


class ARContentBase(BaseModel):
    name: str = Field(..., max_length=255)
    content_metadata: Dict[str, Any] = {}
    
    # Customer information
    order_number: Optional[str] = Field(None, max_length=100)
    customer_name: Optional[str] = Field(None, max_length=255)
    customer_phone: Optional[str] = Field(None, max_length=50)
    customer_email: Optional[str] = Field(None, max_length=255)
    
    # Subscription information
    duration_years: int = Field(default=1, ge=1)
    views_count: int = Field(default=0, ge=0)
    
    # Status
    status: ARContentStatus = ARContentStatus.ACTIVE
    is_active: bool = True
    active_video_id: Optional[int] = None
    rotation_state: int = Field(default=0, ge=0)


class ARContentCreate(ARContentBase):
    company_id: int
    project_id: int
    image_path: str = Field(..., max_length=500)


class ARContentUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    content_metadata: Optional[Dict[str, Any]] = None
    
    # Customer information
    order_number: Optional[str] = Field(None, max_length=100)
    customer_name: Optional[str] = Field(None, max_length=255)
    customer_phone: Optional[str] = Field(None, max_length=50)
    customer_email: Optional[str] = Field(None, max_length=255)
    
    # Subscription information
    duration_years: Optional[int] = Field(None, ge=1)
    views_count: Optional[int] = Field(None, ge=0)
    
    # Status
    status: Optional[ARContentStatus] = None
    is_active: Optional[bool] = None
    active_video_id: Optional[int] = None
    rotation_state: Optional[int] = Field(None, ge=0)


class ARContentVideoUpdate(BaseModel):
    """Schema for updating only the video of AR content."""
    pass  # Video is uploaded as file, this is just for the endpoint signature


class ARContentInDBBase(ARContentBase):
    id: int
    company_id: int
    project_id: int
    unique_id: UUID
    
    # File URLs
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    qr_code_url: Optional[str] = None
    preview_url: Optional[str] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ARContent(ARContentInDBBase):
    pass


class ARContentWithLinks(ARContent):
    """AR Content with additional helper fields."""
    public_link: str
    qr_code_path: str
    
    class Config:
        from_attributes = True


class ARContentList(BaseModel):
    """Response schema for AR content lists."""
    items: list[ARContent]


class ARContentCreateResponse(BaseModel):
    """Response schema for AR content creation."""
    id: int
    unique_id: UUID
    unique_link: str
    image_url: Optional[str]
    video_url: Optional[str] 
    qr_code_url: Optional[str]
    preview_url: Optional[str]