# Base model for SQLAlchemy models

import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class BaseModel(Base):
    """Base model with common fields for all models"""
    __abstract__ = True

    # Use UUID as primary key for new models
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)