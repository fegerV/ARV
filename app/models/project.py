from sqlalchemy import Column, String, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from app.enums import ProjectStatus


class Project(BaseModel):
    """Project model with relationships to Company and AR Content"""
    
    __tablename__ = "projects"

    # Basic information
    name = Column(String(255), nullable=False)
    status = Column(String(50), default=ProjectStatus.ACTIVE, nullable=False)
    company_id = Column(ForeignKey("companies.id"), nullable=False, index=True)

    # Relationships
    company = relationship("Company", back_populates="projects")
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
