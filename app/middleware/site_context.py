"""Middleware that loads site_title from DB settings into ``request.state``.

Templates access it via ``request.state.site_title``.
The value is cached in-memory with a short TTL.
"""

import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

_DEFAULT_TITLE = "Vertex AR Admin"
_cache: dict[str, tuple[str, float]] = {}
_CACHE_TTL = 30.0


async def _fetch_site_title() -> str:
    try:
        from app.core.database import AsyncSessionLocal
        from app.models.settings import SystemSettings
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(SystemSettings.value).where(SystemSettings.key == "site_title")
            )
            raw = result.scalar_one_or_none()
            return raw if raw else _DEFAULT_TITLE
    except Exception:
        return _DEFAULT_TITLE


class SiteContextMiddleware(BaseHTTPMiddleware):
    """Inject ``site_title`` into ``request.state`` for all requests."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        now = time.monotonic()
        cached = _cache.get("site_title")
        if cached and (now - cached[1]) < _CACHE_TTL:
            title = cached[0]
        else:
            title = await _fetch_site_title()
            _cache["site_title"] = (title, now)

        request.state.site_title = title
        return await call_next(request)
