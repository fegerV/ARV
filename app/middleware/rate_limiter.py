"""Rate-limiting middleware.

Uses ``slowapi`` with the real client IP extracted from ``X-Real-IP``
(set by Nginx) so it works correctly behind a reverse proxy.
"""

import time
from typing import Callable

from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import structlog

logger = structlog.get_logger()


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


# Global limiter — default 100 requests / minute per IP
limiter = Limiter(
    key_func=_get_real_ip,
    default_limits=["100/minute"],
    # NOTE: In-memory storage (default). For multi-worker setups switch to
    # Redis backend by setting RATELIMIT_STORAGE_URI in env (see slowapi docs).
    # Example: storage_uri="redis://localhost:6379/1"
)


# ── Setup ────────────────────────────────────────────────────────────

def setup_rate_limiting(app: FastAPI) -> None:
    """Register the slowapi limiter and a middleware that adds real headers."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.middleware("http")
    async def rate_limit_header_middleware(request: Request, call_next):  # type: ignore[override]
        response = await call_next(request)
        # Expose the real client IP as a debug header (helpful for ops)
        response.headers["X-Client-IP"] = _get_real_ip(request)
        return response


# ── Decorator for per-route limits ───────────────────────────────────

def rate_limit(limit_string: str) -> Callable:
    """Apply a per-route rate limit, e.g. ``@rate_limit("5/minute")``."""
    return limiter.limit(limit_string)
