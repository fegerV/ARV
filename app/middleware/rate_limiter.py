"""Rate-limiting middleware.

Uses ``slowapi`` with the real client IP extracted from ``X-Real-IP``
(set by Nginx) so it works correctly behind a reverse proxy.

The default limit is read from the ``api_rate_limit`` DB setting
(requests per minute).  A short in-memory cache avoids hitting
the DB on every request.
"""

import time
from typing import Callable

from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import structlog

logger = structlog.get_logger()

_DEFAULT_RATE = 100  # requests/minute fallback
_cache: dict[str, tuple[int, float]] = {}
_CACHE_TTL = 30.0


def _get_configured_rate() -> int:
    """Return ``api_rate_limit`` from the in-memory cache (sync-safe)."""
    cached = _cache.get("api_rate_limit")
    if cached and (time.monotonic() - cached[1]) < _CACHE_TTL:
        return cached[0]
    return _DEFAULT_RATE


async def _refresh_rate_limit_cache() -> None:
    """Fetch ``api_rate_limit`` from DB and update the cache."""
    try:
        from app.core.database import AsyncSessionLocal
        from app.models.settings import SystemSettings
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(SystemSettings.value).where(SystemSettings.key == "api_rate_limit")
            )
            raw = result.scalar_one_or_none()
            rate = int(raw) if raw else _DEFAULT_RATE
    except Exception:
        rate = _DEFAULT_RATE

    _cache["api_rate_limit"] = (rate, time.monotonic())


# ── Key function ─────────────────────────────────────────────────────

def _get_real_ip(request: Request) -> str:
    """Extract the real client IP from reverse-proxy headers.

    Priority: X-Real-IP → first entry in X-Forwarded-For → direct peer.
    """
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _dynamic_limit() -> str:
    """Return the current default limit string for slowapi."""
    rate = _get_configured_rate()
    return f"{rate}/minute"


# Global limiter — default limit is resolved dynamically
limiter = Limiter(
    key_func=_get_real_ip,
    default_limits=[_dynamic_limit],
)


# ── Setup ────────────────────────────────────────────────────────────

def setup_rate_limiting(app: FastAPI) -> None:
    """Register the slowapi limiter and a middleware that adds real headers."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.middleware("http")
    async def rate_limit_header_middleware(request: Request, call_next):
        # Periodically refresh the cached rate limit
        cached = _cache.get("api_rate_limit")
        if not cached or (time.monotonic() - cached[1]) >= _CACHE_TTL:
            await _refresh_rate_limit_cache()

        response = await call_next(request)
        response.headers["X-Client-IP"] = _get_real_ip(request)
        return response


# ── Decorator for per-route limits ───────────────────────────────────

def rate_limit(limit_string: str) -> Callable:
    """Apply a per-route rate limit, e.g. ``@rate_limit("5/minute")``."""
    return limiter.limit(limit_string)
