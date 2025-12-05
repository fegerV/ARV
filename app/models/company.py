from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    slug = Column(String(255), unique=True, nullable=False)

    # Contacts
    contact_email = Column(String(255))
    contact_phone = Column(String(50))
    telegram_chat_id = Column(String(100))

    # Storage
    storage_connection_id = Column(Integer, ForeignKey("storage_connections.id"))
    storage_path = Column(String(500))

    # Quotas & billing
    subscription_tier = Column(String(50), default="basic")
    storage_quota_gb = Column(Integer, default=10)
    storage_used_bytes = Column(BigInteger, default=0)
    projects_limit = Column(Integer, default=50)

    # Status
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    subscription_expires_at = Column(DateTime)

    # Notes & metadata
    notes = Column(Text)
    company_metadata = Column(JSONB, default={}, name="metadata")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer)  # FK to users.id (omitted)

    # Relationships
    storage_connection = relationship("StorageConnection", back_populates="companies")