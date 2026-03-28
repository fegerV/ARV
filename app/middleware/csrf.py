"""Minimal server-side CSRF protection for cookie-authenticated browser requests."""

from __future__ import annotations

import secrets
from typing import Final

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.config import settings

SAFE_METHODS: Final[set[str]] = {"GET", "HEAD", "OPTIONS", "TRACE"}
CSRF_COOKIE_NAME: Final[str] = "csrf_token"
CSRF_HEADER_NAME: Final[str] = "X-CSRF-Token"
_EXEMPT_PATH_PREFIXES: Final[tuple[str, ...]] = (
    "/api/auth/login",
    "/api/auth/login-form",
    "/admin/login-form",
    "/admin/login-2fa",
)


def _is_exempt_path(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in _EXEMPT_PATH_PREFIXES)


class CSRFMiddleware(BaseHTTPMiddleware):
    """Double-submit CSRF token for requests authenticated by cookies."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        csrf_token = request.cookies.get(CSRF_COOKIE_NAME) or secrets.token_urlsafe(32)
        request.state.csrf_token = csrf_token

        if await self._must_validate(request, csrf_token):
            return self._forbidden_response(request)

        response = await call_next(request)
        if request.cookies.get(CSRF_COOKIE_NAME) != csrf_token:
            response.set_cookie(
                key=CSRF_COOKIE_NAME,
                value=csrf_token,
                path="/",
                secure=settings.is_production,
                httponly=False,
                samesite="lax",
            )
        return response

    async def _extract_submitted_token(self, request: Request) -> str | None:
        header_token = request.headers.get(CSRF_HEADER_NAME)
        if header_token:
            return header_token

        content_type = request.headers.get("content-type", "").lower()
        if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
            form = await request.form()
            token = form.get("csrf_token")
            if isinstance(token, str):
                return token
        return None

    async def _must_validate(self, request: Request, csrf_token: str) -> bool:
        if request.method.upper() in SAFE_METHODS:
            return False
        if _is_exempt_path(request.url.path):
            return False
        if not request.cookies.get("access_token"):
            return False
        submitted = await self._extract_submitted_token(request)
        if not submitted:
            return True
        return not secrets.compare_digest(submitted, csrf_token)

    @staticmethod
    def _forbidden_response(request: Request) -> Response:
        if request.url.path.startswith("/api/"):
            return JSONResponse(status_code=403, content={"detail": "CSRF validation failed"})
        return HTMLResponse("CSRF validation failed", status_code=403)
