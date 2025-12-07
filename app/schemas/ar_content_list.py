from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ARContentListItem(BaseModel):
    id: int
    unique_id: str
    title: str
    description: Optional[str] = None
    
    company_id: int
    company_name: Optional[str] = None
    project_id: int
    project_name: Optional[str] = None
    
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    
    videos_count: int
    marker_status: str
    
    views_count: int
    created_at: datetime
    expires_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True