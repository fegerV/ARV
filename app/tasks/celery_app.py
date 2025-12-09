from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

# Create Celery application
celery_app = Celery(
    "vertex_ar",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.marker_tasks", "app.tasks.notification_tasks", "app.tasks.expiry_tasks", "app.tasks.monitoring", "app.tasks.preview_tasks"],
)

# Configure Celery
celery_app.conf.update(
    task_track_started=settings.CELERY_TASK_TRACK_STARTED,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    result_expires=3600,
    timezone="UTC",
    enable_utc=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_default_queue="default",
    task_queues={
        "markers": {"exchange": "markers", "routing_key": "markers"},
        "notifications": {"exchange": "notifications", "routing_key": "notifications"},
        "default": {"exchange": "default", "routing_key": "default"},
    },
    # Explicitly set the scheduler to avoid import issues
    beat_scheduler="celery.beat:PersistentScheduler",
)

celery_app.conf.beat_schedule = {
    "check-expiring-projects": {
        "task": "app.tasks.expiry_tasks.check_expiring_projects",
        "schedule": crontab(hour=9, minute=0),
    },
    "deactivate-expired-content": {
        "task": "app.tasks.expiry_tasks.deactivate_expired_content",
        "schedule": crontab(minute=0),
    },
    "rotate-videos": {
        "task": "app.tasks.expiry_tasks.rotate_scheduled_videos",
        "schedule": crontab(minute="*/5"),
    },
    # existing daily notification placeholder
    "check-expiring-content": {
        "task": "app.tasks.notification_tasks.check_expiring_content",
        "schedule": crontab(hour=0, minute=0),
    },
    # monitoring health checks
    "system_health_check": {
        "task": "app.tasks.monitoring.system_health_check",
        "schedule": crontab(minute="*/5"),
    },
    "alert_cooldown_manager": {
        "task": "app.tasks.monitoring.alert_cooldown_manager",
        "schedule": crontab(minute="*/1"),
    },
}