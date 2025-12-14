from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class ARViewSession(BaseModel):
    __tablename__ = "ar_view_sessions"

    ar_content_id = Column(UUID(as_uuid=True), ForeignKey("ar_contents.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)

    session_id = Column(UUID(as_uuid=True))

    user_agent = Column(String)
    device_type = Column(String(50))
    browser = Column(String(100))
    os = Column(String(100))

    ip_address = Column(String(64))
    country = Column(String(100))
    city = Column(String(100))

    duration_seconds = Column(Integer)
    tracking_quality = Column(String(50))
    video_played = Column(Boolean, default=False)

    # Relationships
    ar_content = relationship("ARContent")
    project = relationship("Project")
    company = relationship("Company")
