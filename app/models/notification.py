from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
from app.core.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)

    company_id = Column(Integer)
    project_id = Column(Integer)
    ar_content_id = Column(Integer)

    notification_type = Column(String(50), nullable=False)

    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime)
    email_error = Column(Text)

    telegram_sent = Column(Boolean, default=False)
    telegram_sent_at = Column(DateTime)
    telegram_error = Column(Text)

    subject = Column(String(500))
    message = Column(Text)

    notification_metadata = Column("metadata", JSONB, default={})

    created_at = Column(DateTime, default=datetime.utcnow)
