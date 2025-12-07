from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class ARVideoShort(BaseModel):
    id: int
    title: str
    video_url: str
    thumbnail_url: Optional[str] = None
    duration: Optional[float] = None

class ARContentStats(BaseModel):
    views: int
    unique_sessions: int
    avg_duration: float
    avg_fps: float

class RotationRuleShort(BaseModel):
    type: str
    type_human: str
    default_video_title: Optional[str] = None
    next_change_at: Optional[datetime] = None
    next_change_at_readable: Optional[str] = None

class ARContentDetailResponse(BaseModel):
    id: int
    unique_id: str
    title: str
    description: Optional[str] = None

    company_id: int
    company_name: Optional[str]
    project_id: int
    project_name: Optional[str]

    image_url: Optional[str]
    thumbnail_url: Optional[str]
    image_width: Optional[int]
    image_height: Optional[int]
    image_size_readable: Optional[str]
    image_path: Optional[str]

    marker_status: str
    marker_url: Optional[str]
    marker_path: Optional[str]
    marker_feature_points: Optional[int]

    videos: List[ARVideoShort]
    rotation_rule: Optional[RotationRuleShort]
    stats: ARContentStats

    created_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True