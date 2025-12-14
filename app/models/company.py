from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from app.enums import CompanyStatus


class Company(BaseModel):
    """Company model with basic information and relationships"""
    
    __tablename__ = "companies"

    # Basic information
    name = Column(String(255), nullable=False)
    contact_email = Column(String(255))
    status = Column(String(50), default=CompanyStatus.ACTIVE, nullable=False)

    # Relationships
    projects = relationship("Project", back_populates="company", cascade="all, delete-orphan")

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