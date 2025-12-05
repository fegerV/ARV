from sqlalchemy import Column, Integer, String, Time, DateTime, ARRAY
from app.core.database import Base


class VideoRotationSchedule(Base):
    __tablename__ = "video_rotation_schedules"

    id = Column(Integer, primary_key=True)
    ar_content_id = Column(Integer, nullable=False)

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

    created_at = Column(DateTime)
