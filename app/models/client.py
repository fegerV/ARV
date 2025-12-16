from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    
    # Basic information
    name = Column(String(255), nullable=False)
    phone = Column(String(50))
    email = Column(String(255))
    
    # Additional contact info
    address = Column(String(500))
    notes = Column(String(1000))
    
    # Status and timestamps
    is_active = Column(String(50), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    company = relationship("Company", backref="clients")