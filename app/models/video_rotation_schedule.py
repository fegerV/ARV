from sqlalchemy import Column, Integer, String, Time, DateTime, ARRAY, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class VideoRotationSchedule(BaseModel):
    __tablename__ = "video_rotation_schedules"

    ar_content_id = Column(UUID(as_uuid=True), ForeignKey("ar_contents.id"), nullable=False)

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

    # Relationships
    ar_content = relationship("ARContent")
