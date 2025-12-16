from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Folder(Base):
    __tablename__ = "folders"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    
    # Basic information
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Organization
    parent_id = Column(Integer, ForeignKey("folders.id"), nullable=True)
    folder_path = Column(String(500))  # Full path like "folder1/subfolder2"
    
    # Status and metadata
    is_active = Column(String(50), default="active")
    sort_order = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", backref="folders")
    parent = relationship("Folder", remote_side=[id], backref="children")