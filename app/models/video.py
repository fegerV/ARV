from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from app.enums import VideoStatus


class Video(BaseModel):
    __tablename__ = "videos"

    ar_content_id = Column(UUID(as_uuid=True), ForeignKey("ar_contents.id"), nullable=False)
    
    # File information
    file_path = Column(String(500), nullable=False)  # Renamed from video_path for consistency
    public_url = Column(String(500))  # Public access URL
    video_path = Column(String(500), nullable=False)  # Keep for compatibility
    video_url = Column(String(500))  # Keep for compatibility
    thumbnail_url = Column(String(500))
    preview_url = Column(String(500))  # Preview generated from middle frame

    # Video metadata
    title = Column(String(255))
    duration = Column(Float)
    width = Column(Integer)
    height = Column(Integer)
    size_bytes = Column(Integer)
    mime_type = Column(String(100))

    # Status and scheduling
    status = Column(String(50), default=VideoStatus.UPLOADED, nullable=False)  # Use VideoStatus enum
    is_active = Column(Boolean, default=False)  # Default to False, only one should be active
    
    # Subscription management
    subscription_end = Column(DateTime)  # When access to this video expires
    
    # Rotation management - only these three values allowed
    rotation_type = Column(String(20), default="none")  # 'none', 'sequential', 'cyclic'
    rotation_order = Column(Integer, default=0)
    
    # Relationships
    ar_content = relationship("ARContent", back_populates="videos", foreign_keys=[ar_content_id])
    schedules = relationship("VideoSchedule", back_populates="video", cascade="all, delete-orphan")
