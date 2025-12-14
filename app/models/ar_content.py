from sqlalchemy import Column, Integer, String, ForeignKey, Index, CheckConstraint
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from app.enums import ArContentStatus
import re
import uuid


class ARContent(BaseModel):
    """AR Content model representing customer AR content with videos"""
    
    __tablename__ = "ar_contents"
    
    # Foreign Keys
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    active_video_id = Column(UUID(as_uuid=True), ForeignKey("videos.id"), nullable=True)
    
    # Unique identifier for public links
    unique_id = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False, unique=True)
    
    # Order and customer information
    order_number = Column(String(50), nullable=False)
    customer_name = Column(String(255), nullable=True)
    customer_phone = Column(String(50), nullable=True)
    customer_email = Column(String(255), nullable=True)
    
    # Subscription and usage
    duration_years = Column(Integer, default=1, nullable=False)
    views_count = Column(Integer, default=0, nullable=False)
    
    # Status and metadata
    status = Column(String(50), default=ArContentStatus.PENDING, nullable=False)
    content_metadata = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    
    # File storage paths and URLs
    photo_path = Column(String(500), nullable=True)
    photo_url = Column(String(500), nullable=True)
    video_path = Column(String(500), nullable=True)
    video_url = Column(String(500), nullable=True)
    qr_code_path = Column(String(500), nullable=True)
    qr_code_url = Column(String(500), nullable=True)
    
    # Constraints
    __table_args__ = (
        Index('ix_ar_content_unique_id', 'unique_id', unique=True),
        Index('ix_ar_content_project_order', 'project_id', 'order_number', unique=True),
        CheckConstraint('duration_years IN (1, 3, 5)', name='check_duration_years'),
        CheckConstraint('views_count >= 0', name='check_views_count_non_negative'),
    )
    
    # Relationships
    project = relationship("Project", back_populates="ar_contents")
    videos = relationship("Video", back_populates="ar_content", cascade="all, delete-orphan", foreign_keys="Video.ar_content_id")
    active_video = relationship("Video", foreign_keys=[active_video_id])
    
    @property
    def public_link(self) -> str:
        """Generate public link for AR viewer"""
        return f"/view/{self.unique_id}"
    
    @property
    def qr_code_path(self) -> str:
        """Generate QR code file path"""
        return f"/storage/qr/{self.id}.png"
    
    @property
    def company_id(self) -> str:
        """Get company_id from project"""
        return self.project.company_id if self.project else None
    
    def validate_email(self):
        """Validate customer email if provided"""
        if self.customer_email:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, self.customer_email):
                raise ValueError("Invalid email format")
    
    def __repr__(self) -> str:
        return f"<ARContent id={self.id} order_number={self.order_number} status={self.status}>"