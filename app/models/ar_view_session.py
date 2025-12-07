from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float
from sqlalchemy.dialects.postgresql import JSONB, UUID
from datetime import datetime
from app.core.database import Base


class ARViewSession(Base):
    __tablename__ = "ar_view_sessions"

    id = Column(Integer, primary_key=True)
    ar_content_id = Column(Integer, nullable=False)
    project_id = Column(Integer, nullable=False)
    company_id = Column(Integer, nullable=False)

    session_id = Column(UUID(as_uuid=True))

    user_agent = Column(String)
    device_type = Column(String(50))
    browser = Column(String(100))
    os = Column(String(100))

    ip_address = Column(String(64))
    country = Column(String(100))
    city = Column(String(100))

    duration_seconds = Column(Integer)
    avg_fps = Column(Float)
    tracking_quality = Column(String(50))
    video_played = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
