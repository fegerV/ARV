from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from app.enums import VideoStatus


class Video(BaseModel):
    __tablename__ = "videos"

    ar_content_id = Column(UUID(as_uuid=True), ForeignKey("ar_contents.id"), nullable=False)
    
    # File information
    filename = Column(String(255), nullable=False)
    video_path = Column(String(500), nullable=True)
    video_url = Column(String(500), nullable=True)

    thumbnail_path = Column(String(500), nullable=True)
    thumbnail_url = Column(String(500), nullable=True)
    preview_url = Column(String(500), nullable=True)
    
    # Video metadata
    duration = Column(Integer)  # Duration in seconds
    width = Column(Integer)
    height = Column(Integer)
    size_bytes = Column(Integer)  # Size in bytes
    mime_type = Column(String(100))
    
    # Status
    status = Column(String(50), default=VideoStatus.UPLOADED, nullable=False)

    # Playback/rotation
    is_active = Column(Boolean, default=False, nullable=False)
    rotation_type = Column(String(20), default="none", nullable=False)
    rotation_order = Column(Integer, default=0, nullable=False)
    subscription_end = Column(DateTime, nullable=True)
    
    # Relationships
    ar_content = relationship("ARContent", back_populates="videos", foreign_keys=[ar_content_id])
    schedules = relationship("VideoSchedule", back_populates="video", cascade="all, delete-orphan")
