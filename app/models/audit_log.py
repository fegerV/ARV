from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    
    # Entity information
    entity_type = Column(String(100), nullable=False)  # 'user', 'company', 'project', etc.
    entity_id = Column(Integer, nullable=False)
    
    # Action information
    action = Column(String(100), nullable=False)  # 'create', 'update', 'delete', 'login', etc.
    
    # Change details
    changes = Column(JSON().with_variant(JSONB, "postgresql"), default={})  # Before/after values
    field_name = Column(String(100))  # Specific field that changed
    
    # Actor information
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    actor_email = Column(String(255))
    actor_ip = Column(String(64))
    user_agent = Column(Text)
    
    # Additional context
    session_id = Column(String(255))
    request_id = Column(String(255))
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    actor = relationship("User", foreign_keys=[actor_id])