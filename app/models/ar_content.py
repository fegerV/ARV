from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint, Enum as SQLEnum, Float
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
import enum


class ARContentStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PROCESSING = "processing"


class ARContent(Base):
    __tablename__ = "ar_content"
    __table_args__ = (
        UniqueConstraint('unique_id', name='uq_ar_content_unique_id'),
    )

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)

    # Immutable unique identifier
    unique_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)

    # Basic information
    name = Column(String(255), nullable=False)
    content_metadata = Column(JSONB, default={})

    # Customer information
    order_number = Column(String(100))
    customer_name = Column(String(255))
    customer_phone = Column(String(50))
    customer_email = Column(String(255))
    
    # Subscription information
    duration_years = Column(Integer, default=1)
    views_count = Column(Integer, default=0)
    
    # File paths and URLs
    image_path = Column(String(500), nullable=False)
    image_url = Column(String(500))
    
    video_path = Column(String(500))
    video_url = Column(String(500))
    
    qr_code_path = Column(String(500))
    qr_code_url = Column(String(500))
    
    preview_url = Column(String(500))

    # Status and timestamps
    status = Column(SQLEnum(ARContentStatus), default=ARContentStatus.ACTIVE, nullable=False)
    is_active = Column(Boolean, default=True)
    active_video_id = Column(Integer, ForeignKey("videos.id"))  # Currently active video for this AR content
    rotation_state = Column(Integer, default=0)  # Current index for rotation (0-based)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="ar_contents")
    project = relationship("Project", back_populates="ar_contents")
    active_video = relationship("Video", foreign_keys=[active_video_id])
    videos = relationship("Video", back_populates="ar_content", cascade="all, delete-orphan", foreign_keys="Video.ar_content_id")

    @property
    def public_link(self) -> str:
        """Computed property for public AR viewer link"""
        if self.unique_id:
            return f"/ar/{self.unique_id}"
        return ""

    @property
    def qr_code_path(self) -> str:
        """Computed property for QR code file path"""
        if self.unique_id:
            return f"qr_codes/{self.unique_id}.png"
        return ""

    def __repr__(self):
        return f"<ARContent(id={self.id}, name='{self.name}', unique_id='{self.unique_id}', status='{self.status}')>"