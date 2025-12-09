from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from datetime import datetime
from app.core.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, nullable=False)

    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False)
    folder_path = Column(String(500))

    description = Column(Text)
    project_type = Column(String(100))

    subscription_type = Column(String(50), default="monthly")
    starts_at = Column(DateTime)
    expires_at = Column(DateTime)
    auto_renew = Column(Integer, default=0)  # use Boolean if preferred

    status = Column(String(50), default="active")

    notify_before_expiry_days = Column(Integer, default=7)
    last_notification_sent_at = Column(DateTime)

    tags = Column(ARRAY(String))
    project_metadata = Column("metadata", JSONB, default={})

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
