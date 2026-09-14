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

# Only genuinely pre-authentication endpoints are exempt, matched by exact path.
#
# Why this list is deliberately short:
#   * Requests that carry no ``access_token`` cookie are skipped by
#     ``_must_validate`` anyway, so Bearer-token API clients, payment webhooks
#     and provider redirects never need an entry here.
#   * GET/HEAD are already in ``SAFE_METHODS``, so the OAuth ``/authorize`` and
#     ``/callback`` endpoints need no exemption either.
#
# That leaves only the login forms. Everything else that is cookie-
# authenticated and mutates state must present the double-submit token.
#
# The previous version of this list used broad prefixes (``/api/oauth/``) and
# substring matching (``"/yandex-token" in path``), which silently exempted
# state-changing endpoints such as
# ``POST /api/companies/{id}/yandex-auth-code`` (binds a Yandex Disk account to
# a company) and ``DELETE /api/companies/{id}/yandex-token``. Those are
# initiated by our own UI, so they can and must send the token.
_EXEMPT_PATHS: Final[frozenset[str]] = frozenset(
    {
        "/api/auth/login",
        "/api/auth/login-form",
        "/admin/login-form",
        "/admin/login-2fa",
    }
)


def _is_exempt_path(path: str) -> bool:
    """Return True only for the exact pre-authentication login endpoints."""
    return path.rstrip("/") in _EXEMPT_PATHS


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
