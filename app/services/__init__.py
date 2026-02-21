# Services module
# marker_service не импортируем здесь — требует cv2/numpy, ломает тесты без opencv.
# Импорт: from app.services.marker_service import marker_service
from .notification_service import notification_service
from .video_scheduler import get_active_video
from .alert_service import alert_service
from .thumbnail_service import thumbnail_service

__all__ = [
    "notification_service", "get_active_video",
    "alert_service", "thumbnail_service",
]