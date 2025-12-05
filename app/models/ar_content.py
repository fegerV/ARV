from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from datetime import datetime
from app.core.database import Base


class ARContent(Base):
    __tablename__ = "ar_content"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, nullable=False)
    company_id = Column(Integer, nullable=False)

    unique_id = Column(UUID(as_uuid=True), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)

    image_path = Column(String(500), nullable=False)
    image_url = Column(String(500))
    thumbnail_url = Column(String(500))

    marker_path = Column(String(500))
    marker_url = Column(String(500))
    marker_status = Column(String(50), default="pending")
    marker_generated_at = Column(DateTime)

    active_video_id = Column(Integer)

    video_rotation_enabled = Column(Boolean, default=False)
    video_rotation_type = Column(String(50))

    is_active = Column(Boolean, default=True)
    published_at = Column(DateTime)
    expires_at = Column(DateTime)

    qr_code_path = Column(String(500))
    qr_code_url = Column(String(500))

    views_count = Column(Integer, default=0)
    last_viewed_at = Column(DateTime)

    metadata = Column(JSONB, default={})

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
