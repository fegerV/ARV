from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.core.database import Base


class EmailQueue(Base):
    __tablename__ = "email_queue"

    id = Column(Integer, primary_key=True)
    
    # Email details
    recipient_to = Column(String(255), nullable=False)
    recipient_cc = Column(String(255))
    recipient_bcc = Column(String(255))
    subject = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    html = Column(Text)
    
    # Template information
    template_id = Column(String(100))
    variables = Column(JSON().with_variant(JSONB, "postgresql"), default={})
    
    # Status tracking
    status = Column(String(50), default="pending")  # pending, sent, failed, cancelled
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    
    # Error handling
    last_error = Column(Text)
    
    # Priority and scheduling
    priority = Column(Integer, default=5)  # 1-10, lower number = higher priority
    scheduled_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    sent_at = Column(DateTime)