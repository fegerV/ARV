from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class StorageConnection(Base):
    __tablename__ = "storage_connections"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    provider = Column(String(50), nullable=False)  # 'local_disk', 'minio', 'yandex_disk'

    # Provider-specific configuration (local_disk may not require credentials)
    credentials = Column(JSONB, nullable=True, default={})

    # For local_disk
    base_path = Column(String(500))

    # Default connection (only for Vertex AR)
    is_default = Column(Boolean, default=False)

    # Status
    is_active = Column(Boolean, default=True)
    last_tested_at = Column(DateTime)
    test_status = Column(String(50))
    test_error = Column(Text)

    storage_metadata = Column("metadata", JSONB, default={})

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, nullable=True)  # FK omitted until users table exists

    # Relationships
    companies = relationship("Company", back_populates="storage_connection")


class StorageFolder(Base):
    __tablename__ = "storage_folders"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"))

    name = Column(String(255), nullable=False)
    path = Column(String(500), nullable=False)
    folder_type = Column(String(50))  # 'portraits', 'videos', 'markers', 'custom'

    # Stats
    files_count = Column(Integer, default=0)
    total_size_bytes = Column(BigInteger, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="folders")