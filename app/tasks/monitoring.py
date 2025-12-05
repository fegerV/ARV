from datetime import datetime
import psutil
import httpx
import structlog

from app.tasks.celery_app import celery_app
from app.core.config import settings
from app.services.alert_service import Alert, send_critical_alerts

logger = structlog.get_logger()


@celery_app.task(name="app.tasks.monitoring.system_health_check")
def system_health_check():
    """Комплексная проверка системы + критические алерты."""
    # Collect metrics
    metrics = {
        "timestamp": datetime.utcnow().isoformat(),
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("/").percent,
        "celery_queue_length": 0,
        "api_health": "unknown",
    }

    # Check API health
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get("http://app:8000/api/health/status")
            if resp.status_code == 200:
                data = resp.json()
                metrics["api_health"] = data.get("overall", "unknown")
                celery_info = data.get("celery", {})
                metrics["celery_queue_length"] = celery_info.get("queue_length", 0)
    except Exception as e:
        metrics["api_health"] = "unhealthy"
        logger.error("api_health_check_failed", error=str(e))

    alerts: list[Alert] = []

    # Critical thresholds
    if metrics["api_health"] == "critical":
        alerts.append(Alert(
            severity="critical",
            title="Service degraded",
            message="Overall health is critical",
            metrics=metrics,
            affected_services=["app"],
        ))

    if metrics["cpu_percent"] >= 90:
        alerts.append(Alert(
            severity="critical",
            title="High CPU",
            message=f"CPU usage {metrics['cpu_percent']}%",
            metrics=metrics,
            affected_services=["app"],
        ))

    if metrics["memory_percent"] >= 90:
        alerts.append(Alert(
            severity="critical",
            title="High Memory",
            message=f"RAM usage {metrics['memory_percent']}%",
            metrics=metrics,
            affected_services=["app"],
        ))

    if metrics["celery_queue_length"] > 100:
        alerts.append(Alert(
            severity="critical",
            title="Queue backlog",
            message=f"Celery queue length {metrics['celery_queue_length']}",
            metrics=metrics,
            affected_services=["celery"],
        ))

    # Send alerts
    try:
        if alerts:
            # Use cooldown via alert_service implementation
            import asyncio
            asyncio.run(send_critical_alerts(alerts, metrics))
            logger.warning("critical_alerts_sent", count=len(alerts))
    except Exception as e:
        logger.error("critical_alerts_failed", error=str(e))

    # Persist metrics (placeholder)
    logger.info("system_health_metrics", **metrics)

    return {"alerts": len(alerts), "metrics": metrics}


@celery_app.task(name="app.tasks.monitoring.alert_cooldown_manager")
def alert_cooldown_manager():
    """Cooldown housekeeping (Redis TTL handles expiry; no-op)."""
    logger.info("alert_cooldown_manager_tick", ts=datetime.utcnow().isoformat())
    return True
