from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from app.core.database import Base


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True)
    ar_content_id = Column(Integer, nullable=False)

    video_path = Column(String(500), nullable=False)
    video_url = Column(String(500))
    thumbnail_url = Column(String(500))

    title = Column(String(255))
    duration = Column(Float)
    width = Column(Integer)
    height = Column(Integer)
    size_bytes = Column(Integer)
    mime_type = Column(String(100))

    is_active = Column(Boolean, default=False)

    schedule_start = Column(DateTime)
    schedule_end = Column(DateTime)

    rotation_order = Column(Integer, default=0)

    created_at = Column(DateTime)
    updated_at = Column(DateTime)
