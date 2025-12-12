from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID


class ARContentBase(BaseModel):
    name: str = Field(..., max_length=255)
    content_metadata: Dict[str, Any] = {}


class ARContentCreate(ARContentBase):
    company_id: int
    project_id: int


class ARContentUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    content_metadata: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


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
    
    # Status
    is_active: bool
    
    # Timestamps
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ARContent(ARContentInDBBase):
    pass


class ARContentWithLinks(ARContent):
    """AR Content with additional helper fields."""
    unique_link: str
    
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