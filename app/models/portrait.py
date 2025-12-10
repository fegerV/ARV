from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from datetime import datetime
from app.core.database import Base


class Portrait(Base):
    __tablename__ = "portraits"

    id = Column(Integer, primary_key=True, index=True)
    unique_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    
    # Relationships
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    folder_id = Column(Integer, ForeignKey("folders.id"), nullable=True)
    
    # File information
    file_path = Column(String(500), nullable=False)  # Renamed from image_path for consistency
    public_url = Column(String(500))  # Public access URL
    image_path = Column(String(500))  # Keep for compatibility
    image_url = Column(String(500))   # Keep for compatibility
    thumbnail_path = Column(String(500))
    
    # Status and lifecycle
    status = Column(String(50), default="active")  # 'active', 'inactive', 'archived'
    subscription_end = Column(DateTime)
    lifecycle_status = Column(String(50), default="active")  # 'active', 'expiring', 'expired', 'suspended'
    
    # Notification tracking
    notified_7d = Column(Boolean, default=False)  # Notified 7 days before expiry
    notified_24h = Column(Boolean, default=False)  # Notified 24 hours before expiry
    notified_expired = Column(Boolean, default=False)  # Notified after expiry

    # Mind AR marker
    marker_path = Column(String(500))
    marker_url = Column(String(500))
    marker_status = Column(String(50), default="pending", index=True)

    # Metadata
    storage_connection_id = Column(Integer, nullable=True)
    storage_folder_id = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    company = relationship("Company", backref="portraits")
    client = relationship("Client", backref="portraits")
    folder = relationship("Folder", backref="portraits")
