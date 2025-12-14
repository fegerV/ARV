from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, BigInteger, ForeignKey, select, func
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
    company_metadata = Column("metadata", JSONB, default={})

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer)  # FK to users.id (omitted)

    # Relationships
    projects = relationship("Project", back_populates="company", cascade="all, delete-orphan")
    ar_contents = relationship("ARContent", back_populates="company", cascade="all, delete-orphan")

    @property
    def projects_count(self) -> int:
        """Computed property for number of projects"""
        if hasattr(self, '_projects_count'):
            return self._projects_count
        # This would be computed in a query with a subquery
        return len(self.projects) if self.projects else 0

    @property
    def ar_content_count(self) -> int:
        """Computed property for number of AR content items"""
        if hasattr(self, '_ar_content_count'):
            return self._ar_content_count
        # This would be computed in a query with a subquery
        return len(self.ar_contents) if self.ar_contents else 0

    def __repr__(self):
        return f"<Company(id={self.id}, name='{self.name}', slug='{self.slug}', active={self.is_active})>"