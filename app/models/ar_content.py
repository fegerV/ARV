from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class ARContent(Base):
    __tablename__ = "ar_content"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)

    unique_id = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)

    # изображение
    image_path = Column(String(500))
    image_url = Column(String(500))
    thumbnail_url = Column(String(500))
    image_metadata = Column(JSONB, nullable=True)  # width/height/size_readable

    # маркер
    marker_path = Column(String(500))
    marker_url = Column(String(500))
    marker_status = Column(String(32), default="pending", nullable=False)  # pending/processing/ready/failed
    marker_metadata = Column(JSONB, nullable=True)  # feature_points, quality

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    expires_at = Column(DateTime, nullable=True)

    # связи
    company = relationship("Company", back_populates="ar_contents")
    project = relationship("Project", back_populates="ar_contents")
    videos = relationship("Video", back_populates="ar_content", cascade="all, delete-orphan")
    rotation_rule = relationship(
        "VideoRotationSchedule",
        back_populates="ar_content",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Индексы
    __table_args__ = (
        Index('ix_ar_content_unique_id', unique_id, unique=True),
        Index('ix_ar_content_company_id', company_id),
        Index('ix_ar_content_project_id', project_id),
    )
