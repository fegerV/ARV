from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
import enum


class ProjectStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(SQLEnum(ProjectStatus), default=ProjectStatus.ACTIVE, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="projects")
    ar_contents = relationship("ARContent", back_populates="project", cascade="all, delete-orphan")

    @property
    def ar_content_count(self) -> int:
        """Computed property for number of AR content items"""
        if hasattr(self, '_ar_content_count'):
            return self._ar_content_count
        return len(self.ar_contents) if self.ar_contents else 0

    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}', company_id={self.company_id}, status='{self.status}')>"