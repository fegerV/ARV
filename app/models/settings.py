from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class SystemSettings(Base):
    """System settings model."""
    __tablename__ = "system_settings"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    data_type = Column(String(20), default="string")  # string, integer, boolean, json
    category = Column(String(50), default="general")
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False)  # Can be exposed to frontend
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<SystemSettings(key='{self.key}', category='{self.category}')>"