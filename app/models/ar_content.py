from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from datetime import datetime
from app.core.database import Base


class ARContent(Base):
    __tablename__ = "ar_content"
    __table_args__ = (
        UniqueConstraint('unique_id', name='uq_ar_content_unique_id'),
    )

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, nullable=False, index=True)
    project_id = Column(Integer, nullable=False, index=True)

    # Immutable unique identifier
    unique_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)

    # Basic information
    name = Column(String(255), nullable=False)
    content_metadata = Column(JSONB, default={})

    # File paths and URLs
    image_path = Column(String(500), nullable=False)
    image_url = Column(String(500))
    
    video_path = Column(String(500))
    video_url = Column(String(500))
    
    qr_code_path = Column(String(500))
    qr_code_url = Column(String(500))
    
    preview_url = Column(String(500))

    # Status and timestamps
    is_active = Column(Boolean, default=True)
    active_video_id = Column(Integer)  # Currently active video for this AR content
    rotation_state = Column(Integer, default=0)  # Current index for rotation (0-based)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)