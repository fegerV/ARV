from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True)
    ar_content_id = Column(Integer, ForeignKey("ar_content.id"), nullable=False)
    
    # File information
    file_path = Column(String(500), nullable=False)
    public_url = Column(String(500))
    video_path = Column(String(500), nullable=False)
    video_url = Column(String(500))
    thumbnail_url = Column(String(500))
    preview_url = Column(String(500))

    # Video metadata
    title = Column(String(255))
    duration = Column(Float)
    width = Column(Integer)
    height = Column(Integer)
    size_bytes = Column(Integer)
    mime_type = Column(String(100))

    # Status
    status = Column(String(50), default="active")
    is_active = Column(Boolean, default=False)  # Contextual flag for active video
    
    # Subscription management
    subscription_end = Column(DateTime)
    
    # Rotation management
    rotation_type = Column(String(20), default="none")
    rotation_order = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ar_content = relationship("ARContent", back_populates="videos")
    schedules = relationship("VideoSchedule", back_populates="video", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Video(id={self.id}, title='{self.title}', ar_content_id={self.ar_content_id}, is_active={self.is_active})>"