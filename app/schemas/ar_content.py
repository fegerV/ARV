from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr, validator
from app.enums import ArContentStatus


class ArContentCreate(BaseModel):
    project_id: UUID
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[EmailStr] = None
    duration_years: int = Field(default=1)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @validator('duration_years')
    def validate_duration_years(cls, v):
        if v not in [1, 3, 5]:
            raise ValueError('duration_years must be one of: 1, 3, 5')
        return v
    
    class Config:
        from_attributes = True


class ArContentUpdate(BaseModel):
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[EmailStr] = None
    status: Optional[ArContentStatus] = None
    duration_years: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @validator('duration_years')
    def validate_duration_years(cls, v):
        if v is not None and v not in [1, 3, 5]:
            raise ValueError('duration_years must be one of: 1, 3, 5')
        return v
    
    class Config:
        from_attributes = True


class VideoResponse(BaseModel):
    id: UUID
    ar_content_id: UUID
    filename: str
    duration: Optional[int] = None
    size: Optional[int] = None
    video_status: str
    created_at: str
    
    class Config:
        from_attributes = True


class ArContentResponse(BaseModel):
    id: UUID
    order_number: str
    project_id: UUID
    company_id: Optional[str] = None  # computed
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    duration_years: int
    views_count: int
    status: str
    active_video_id: Optional[UUID] = None
    public_link: str  # computed
    qr_code_path: str  # computed
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class ArContentDetailResponse(ArContentResponse):
    videos: List[VideoResponse] = []
    active_video: Optional[VideoResponse] = None
    
    class Config:
        from_attributes = True


# Additional schemas for API compatibility
class ARContent(ArContentResponse):
    """Alias for ArContentResponse for backward compatibility"""
    pass


class ARContentVideoUpdate(BaseModel):
    """Schema for updating the active video of AR content"""
    active_video_id: UUID
    
    class Config:
        from_attributes = True


class ARContentList(BaseModel):
    """Schema for AR content list response"""
    items: List[ArContentResponse]
    total: int
    page: int
    size: int
    
    class Config:
        from_attributes = True


class ARContentCreateResponse(BaseModel):
    """Schema for AR content creation response"""
    id: UUID
    order_number: str
    public_link: str
    qr_code_url: str
    
    class Config:
        from_attributes = True


class ARContentWithLinks(BaseModel):
    """Schema for AR content with additional links"""
    id: UUID
    order_number: str
    public_link: str
    qr_code_url: str
    views_count: int
    status: str
    
    class Config:
        from_attributes = True


# Aliases for backward compatibility with existing API routes
ARContentCreate = ArContentCreate
ARContentUpdate = ArContentUpdate