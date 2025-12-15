from sqlalchemy import Column, Integer, String, ForeignKey, Index, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid
from datetime import datetime
from app.enums import ProjectStatus


class Project(Base):
    """Project model with relationships to Company and AR Content"""
    
    __tablename__ = "projects"
    
    # Use Integer as primary key to match migration
    id = Column(Integer, primary_key=True, index=True)
    
    # Basic information
    name = Column(String(255), nullable=False)
    status = Column(String(50), default=ProjectStatus.ACTIVE, nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    company = relationship("Company", back_populates="projects")
    # Исправляем ссылку на правильное имя таблицы
    ar_contents = relationship("ARContent", back_populates="project", cascade="all, delete-orphan")
    
    # Index for unique names within company
    __table_args__ = (
        Index('ix_project_company_name', 'company_id', 'name'),
    )

    @property
    def ar_content_count(self) -> int:
        """Count of AR content for this project"""
        return len(self.ar_contents) if self.ar_contents else 0

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name} status={self.status}>"