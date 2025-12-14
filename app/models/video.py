from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from app.enums import VideoStatus


class Video(BaseModel):
    __tablename__ = "videos"

    ar_content_id = Column(UUID(as_uuid=True), ForeignKey("ar_contents.id"), nullable=False)
    
    # File information
    filename = Column(String(255), nullable=False)
    
    # Video metadata
    duration = Column(Integer)  # Duration in seconds
    size = Column(Integer)  # Size in bytes
    
    # Status
    video_status = Column(String(50), default=VideoStatus.UPLOADED, nullable=False)
    
    # Relationships
    ar_content = relationship("ARContent", back_populates="videos", foreign_keys=[ar_content_id])
