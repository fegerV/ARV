"""Storage connection and folder models."""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class StorageConnection(Base):
    __tablename__ = "storage_connections"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    provider = Column(String(50), nullable=False, default="local_disk")
    base_path = Column(String(500), nullable=False)

    is_default = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_tested_at = Column(DateTime)
    test_status = Column(String(50))
    test_error = Column(Text)

    storage_metadata = Column("metadata", JSON().with_variant(JSONB, "postgresql"), default={})

    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)
    created_by = Column(Integer, nullable=True)


class StorageFolder(Base):
    __tablename__ = "storage_folders"

    __table_args__ = (
        Index("ix_storage_folders_company_id", "company_id"),
    )

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)

    name = Column(String(255), nullable=False)
    path = Column(String(500), nullable=False)
    folder_type = Column(String(50))

    files_count = Column(Integer, default=0, nullable=False)
    total_size_bytes = Column(BigInteger, default=0, nullable=False)

    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)
