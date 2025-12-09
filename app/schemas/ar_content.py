from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ARContentBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    
    # Client information
    client_name: Optional[str] = Field(None, max_length=255)
    client_phone: Optional[str] = Field(None, max_length=50)
    client_email: Optional[str] = Field(None, max_length=255)
    
    # Image and thumbnail
    image_path: str = Field(..., max_length=500)
    image_url: Optional[str] = Field(None, max_length=500)
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    
    # Marker information
    marker_path: Optional[str] = Field(None, max_length=500)
    marker_url: Optional[str] = Field(None, max_length=500)
    marker_status: str = "pending"
    marker_generated_at: Optional[datetime] = None
    
    # Video rotation
    video_rotation_enabled: bool = False
    video_rotation_type: Optional[str] = None
    
    # Status and dates
    is_active: bool = True
    published_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    # QR code
    qr_code_path: Optional[str] = Field(None, max_length=500)
    qr_code_url: Optional[str] = Field(None, max_length=500)
    
    # Analytics
    views_count: int = 0
    last_viewed_at: Optional[datetime] = None
    
    # Metadata
    content_metadata: Dict[str, Any] = {}


class ARContentCreate(ARContentBase):
    project_id: int
    company_id: int


class ARContentUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    
    # Client information
    client_name: Optional[str] = Field(None, max_length=255)
    client_phone: Optional[str] = Field(None, max_length=50)
    client_email: Optional[str] = Field(None, max_length=255)
    
    # Image and thumbnail
    image_path: Optional[str] = Field(None, max_length=500)
    image_url: Optional[str] = Field(None, max_length=500)
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    
    # Marker information
    marker_path: Optional[str] = Field(None, max_length=500)
    marker_url: Optional[str] = Field(None, max_length=500)
    marker_status: Optional[str] = None
    marker_generated_at: Optional[datetime] = None
    
    # Video rotation
    video_rotation_enabled: Optional[bool] = None
    video_rotation_type: Optional[str] = None
    
    # Status and dates
    is_active: Optional[bool] = None
    published_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    # QR code
    qr_code_path: Optional[str] = Field(None, max_length=500)
    qr_code_url: Optional[str] = Field(None, max_length=500)
    
    # Analytics
    views_count: Optional[int] = None
    last_viewed_at: Optional[datetime] = None
    
    # Metadata
    content_metadata: Optional[Dict[str, Any]] = None


class ARContentInDBBase(ARContentBase):
    id: int
    project_id: int
    company_id: int
    unique_id: str
    
    active_video_id: Optional[int] = None
    
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ARContent(ARContentInDBBase):
    pass


class ARContentWithVideos(ARContentInDBBase):
    # This would include related videos if needed
    pass