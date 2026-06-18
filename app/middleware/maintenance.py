"""Maintenance mode middleware.

When ``maintenance_mode`` is enabled in system settings, all public-facing
requests return 503 Service Unavailable. Admin routes (``/admin``,
``/settings``, ``/api/auth``, ``/api/health``) remain accessible so the
operator can disable the flag.

The setting is cached for a short TTL to avoid a DB query on every request.
"""

import time

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

import structlog

logger = structlog.get_logger()

_BYPASS_PREFIXES = (
    "/admin",
    "/settings",
    "/api/auth",
    "/api/health",
    "/api/settings",
    "/static",
    "/docs",
    "/redoc",
    "/openapi.json",
)

_MAINTENANCE_HTML = """<!DOCTYPE html>
<html lang="ru">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Техническое обслуживание</title>
<style>
  body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
       font-family:system-ui,-apple-system,sans-serif;background:#0f172a;color:#e2e8f0}
  .c{max-width:32rem;text-align:center;padding:2rem}
  h1{font-size:1.5rem;margin-bottom:.5rem}
  p{color:#94a3b8;font-size:.95rem;line-height:1.6}
  .icon{font-size:3rem;margin-bottom:1rem}
</style></head>
<body><div class="c"><div class="icon">🛠</div>
<h1>Платформа временно недоступна</h1>
<p>На сайте проводятся технические работы. Пожалуйста, попробуйте открыть страницу немного позже.</p>
</div></body></html>"""

# In-memory cache: (value, fetched_at)
_cache: dict[str, tuple[bool, float]] = {}
_CACHE_TTL = 10.0  # seconds


async def _is_maintenance_on() -> bool:
    """Check ``maintenance_mode`` setting with a short in-memory cache."""
    now = time.monotonic()
    cached = _cache.get("maintenance_mode")
    if cached and (now - cached[1]) < _CACHE_TTL:
        return cached[0]

    try:
        from app.core.database import AsyncSessionLocal
        from app.models.settings import SystemSettings
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(SystemSettings.value).where(SystemSettings.key == "maintenance_mode")
            )
            row = result.scalar_one_or_none()
            enabled = row is not None and row.lower() == "true"
    except Exception:
        enabled = False

    _cache["maintenance_mode"] = (enabled, now)
    return enabled


class MaintenanceModeMiddleware(BaseHTTPMiddleware):
    """Return 503 for public requests when maintenance_mode is enabled."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        if any(path.startswith(p) for p in _BYPASS_PREFIXES):
            return await call_next(request)

        if await _is_maintenance_on():
            accept = request.headers.get("accept", "")
            if "application/json" in accept:
                return JSONResponse(
                    {"detail": "Service temporarily unavailable (maintenance)"},
                    status_code=503,
                )
            return HTMLResponse(_MAINTENANCE_HTML, status_code=503)

        return await call_next(request)
