from sqlalchemy import Column, Integer, String, JSON, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.core.database import Base


class Portrait(Base):
    __tablename__ = "portraits"

    id = Column(Integer, primary_key=True, index=True)
    unique_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)

    # File paths
    image_path = Column(String(500), nullable=False)
    image_url = Column(String(500))
    thumbnail_path = Column(String(500))

    # Mind AR marker
    marker_path = Column(String(500))
    marker_url = Column(String(500))
    marker_status = Column(String(50), default="pending", index=True)

    # Metadata
    storage_connection_id = Column(Integer, nullable=True)
    storage_folder_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
