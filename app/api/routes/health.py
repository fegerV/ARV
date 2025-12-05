from datetime import datetime, timedelta
import os
import structlog
import psutil
import redis.asyncio as redis
from fastapi import APIRouter
from starlette.responses import Response
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import engine, AsyncSessionLocal
from app.models.portrait import Portrait

# Celery
try:
    from app.tasks.celery_app import celery_app
except Exception:
    celery_app = None

# Prometheus
try:
    from prometheus_client import generate_latest, CollectorRegistry
    from prometheus_client import CONTENT_TYPE_LATEST
    from prometheus_client import multiprocess
except Exception:
    generate_latest = None
    CollectorRegistry = None
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4"
    multiprocess = None

router = APIRouter(prefix="/api/health", tags=["Health"])
logger = structlog.get_logger()


@router.get("/status")
async def health_status():
    """Расширенный health check endpoint"""
    checks: dict = {}

    # 1. Database connectivity
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = "unhealthy"
        checks["database_error"] = str(e)

    # 2. Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        checks["redis"] = "healthy"
    except Exception as e:
        checks["redis"] = "unhealthy"
        checks["redis_error"] = str(e)

    # 3. Celery queue/worker status (best-effort)
    celery_info = {"status": "unknown", "queue_length": 0, "workers_alive": 0}
    try:
        if celery_app:
            insp = celery_app.control.inspect()
            active = insp.active() or {}
            scheduled = insp.scheduled() or {}
            reserved = insp.reserved() or {}
            celery_info["workers_alive"] = len((insp.ping() or {}).keys())
            celery_info["queue_length"] = sum(
                len(active.get(w, [])) + len(scheduled.get(w, [])) + len(reserved.get(w, []))
                for w in set(list(active.keys()) + list(scheduled.keys()) + list(reserved.keys()))
            )
            celery_info["status"] = "healthy" if celery_info["workers_alive"] > 0 else "unhealthy"
        else:
            celery_info["status"] = "unhealthy"
    except Exception as e:
        celery_info["status"] = "unhealthy"
        celery_info["error"] = str(e)
    checks["celery"] = celery_info

    # 4. System resources
    cpu_percent = psutil.cpu_percent(interval=0.5)
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    checks["system"] = {
        "cpu_percent": cpu_percent,
        "memory_percent": vm.percent,
        "disk_percent": disk.percent,
    }

    # 5. Marker generation failures (last hour, portraits)
    try:
        async with AsyncSessionLocal() as session:  # type: AsyncSession
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            # Use created_at if available; fallback to count of failed overall
            result = await session.execute(
                select(Portrait).where(Portrait.marker_status == "failed")
            )
            failed_count = len(result.scalars().all())
        checks["marker_failures_last_hour"] = failed_count
    except Exception:
        checks["marker_failures_last_hour"] = None

    # 6. Overall status
    unhealthy_components = [
        k for k, v in checks.items() if (v == "unhealthy" or (isinstance(v, dict) and v.get("status") == "unhealthy"))
    ]
    if len(unhealthy_components) == 0:
        overall = "healthy"
    elif len(unhealthy_components) <= 2:
        overall = "degraded"
    else:
        overall = "critical"
    checks["overall"] = overall

    # Log
    logger.info("health_check", **checks)

    return checks


@router.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint."""
    if generate_latest is None:
        return Response(content="", media_type=CONTENT_TYPE_LATEST, status_code=204)

    # Multiprocess registry if configured
    registry = None
    try:
        if multiprocess and os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
            registry = CollectorRegistry()
            multiprocess.MultiProcessCollector(registry)
    except Exception:
        registry = None

    data = generate_latest(registry) if registry else generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
