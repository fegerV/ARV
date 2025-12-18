from sqlalchemy import Column, Integer, String, Time, DateTime, ARRAY, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid
from datetime import datetime


class VideoRotationSchedule(Base):
    __tablename__ = "video_rotation_schedules"
    
    # Use Integer as primary key to match migration
    id = Column(Integer, primary_key=True, index=True)
    
    # Исправляем ссылку на правильное имя таблицы
    ar_content_id = Column(Integer, ForeignKey("ar_content.id"), nullable=False)

    rotation_type = Column(String(50), nullable=False)

    time_of_day = Column(Time)
    day_of_week = Column(Integer)
    day_of_month = Column(Integer)
    cron_expression = Column(String(100))

    video_sequence = Column(ARRAY(Integer))
    current_index = Column(Integer, default=0)

    is_active = Column(Integer, default=1)  # use Boolean if preferred
    last_rotation_at = Column(DateTime)
    next_rotation_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    ar_content = relationship("ARContent")