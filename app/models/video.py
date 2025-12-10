from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True)
    portrait_id = Column(Integer, ForeignKey("portraits.id"), nullable=False)  # Updated from ar_content_id
    
    # File information
    file_path = Column(String(500), nullable=False)  # Renamed from video_path for consistency
    public_url = Column(String(500))  # Public access URL
    video_path = Column(String(500), nullable=False)  # Keep for compatibility
    video_url = Column(String(500))  # Keep for compatibility
    thumbnail_url = Column(String(500))

    # Video metadata
    title = Column(String(255))
    duration = Column(Float)
    width = Column(Integer)
    height = Column(Integer)
    size_bytes = Column(Integer)
    mime_type = Column(String(100))

    # Status and scheduling
    status = Column(String(50), default="active")  # 'active', 'inactive', 'processing'
    is_active = Column(Boolean, default=True)
    
    # Scheduling and rotation
    schedule_start = Column(DateTime)
    schedule_end = Column(DateTime)
    rotation_type = Column(String(50))  # 'daily', 'weekly', 'monthly', 'custom'
    rotation_order = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    
    # Relationships
    portrait = relationship("Portrait", backref="videos")
