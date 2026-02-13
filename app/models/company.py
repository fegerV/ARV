from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base
from app.enums import CompanyStatus, StorageProviderType


class Company(Base):
    """Company model with basic information and relationships"""
    
    __tablename__ = "companies"
    
    # Use Integer as primary key to match migration
    id = Column(Integer, primary_key=True, index=True)
    
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
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    projects = relationship("Project", back_populates="company", cascade="all, delete-orphan")
    # Исправляем ссылку на правильное имя таблицы
    ar_contents = relationship("ARContent", back_populates="company", cascade="all, delete-orphan")

    @property
    def projects_count(self) -> int:
        """Count of projects for this company"""
        return len(self.projects) if self.projects else 0

    @property
    def ar_content_count(self) -> int:
        """Count of AR content across all projects for this company"""
        if not self.projects:
            return 0
        
        total = 0
        for project in self.projects:
            if hasattr(project, 'ar_contents') and project.ar_contents:
                total += len(project.ar_contents)
        return total

    def __repr__(self) -> str:
        return f"<Company id={self.id} name={self.name} status={self.status}>"