from datetime import datetime, timedelta
import os
import structlog
import psutil
from fastapi import APIRouter
from starlette.responses import Response
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import engine, AsyncSessionLocal

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

    # 3. System resources
    cpu_percent = psutil.cpu_percent(interval=0.5)
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    checks["system"] = {
        "cpu_percent": cpu_percent,
        "memory_percent": vm.percent,
        "disk_percent": disk.percent,
    }

    # 5. Overall status
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
