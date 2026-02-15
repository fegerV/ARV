"""Company model."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.enums import CompanyStatus, StorageProviderType


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Company(Base):
    """Company model with basic information and relationships."""

    __tablename__ = "companies"

    __table_args__ = (
        Index("ix_companies_slug", "slug", unique=True),
    )

    id = Column(Integer, primary_key=True)

    # Basic information
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False)
    contact_email = Column(String(255))
    status = Column(String(50), default=CompanyStatus.ACTIVE, nullable=False)

    # Storage provider
    storage_provider = Column(
        String(50),
        default=StorageProviderType.LOCAL,
        server_default="local",
        nullable=False,
    )
    yandex_disk_token = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relationships
    projects = relationship("Project", back_populates="company", cascade="all, delete-orphan")
    ar_contents = relationship("ARContent", back_populates="company", cascade="all, delete-orphan")

    # NOTE: projects_count / ar_content_count properties removed — they
    # triggered lazy-loading (MissingGreenlet in async).  Use explicit
    # COUNT queries in the route/service layer instead.

    def __repr__(self) -> str:
        return f"<Company id={self.id} name={self.name} status={self.status}>"
