"""Regression tests for the CSRF double-submit exemptions.

Background
----------
``_is_exempt_path`` previously matched broad prefixes and substrings:

    "/api/oauth/" prefix                 -> exempted every /api/oauth/* route
    "/yandex-token" in path              -> exempted DELETE .../yandex-token
    "/yandex-auth-code" in path          -> exempted POST  .../yandex-auth-code

Both of those endpoints are cookie-authenticated and state-changing, so they
were reachable without a CSRF token. ``POST /api/companies/{id}/yandex-auth-code``
binds a Yandex Disk account to a company — an attacker who wins that request
gets the tenant's subsequent media uploads written to their own storage
account. ``DELETE /api/companies/{id}/yandex-token`` detaches the tenant's
storage.

The exemption was only ever a workaround for ``templates/companies/form.html``
not sending the header; that call site now sends it, so the exemptions are gone.

These tests pin both the new allow-list and the "no mutating route is exempt"
property, which is what actually prevents the regression from coming back when
new routes are added.
"""

import pytest
from starlette.requests import Request
from starlette.responses import Response

from app.middleware.csrf import (
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    CSRFMiddleware,
    _is_exempt_path,
)

# Endpoints that were incorrectly exempted before the fix.
PREVIOUSLY_EXEMPT_MUTATING_PATHS = (
    "/api/companies/1/yandex-auth-code",
    "/api/companies/1/yandex-token",
    "/api/oauth/1/create-folder",
)

LOGIN_PATHS = (
    "/api/auth/login",
    "/api/auth/login-form",
    "/admin/login-form",
    "/admin/login-2fa",
)


# ----------------------------------------------------------------------
# Allow-list
# ----------------------------------------------------------------------


@pytest.mark.parametrize("path", LOGIN_PATHS)
def test_login_endpoints_remain_exempt(path):
    assert _is_exempt_path(path) is True


def test_login_endpoints_are_exempt_with_a_trailing_slash():
    assert _is_exempt_path("/api/auth/login/") is True


@pytest.mark.parametrize("path", PREVIOUSLY_EXEMPT_MUTATING_PATHS)
def test_previously_exempt_state_changing_endpoints_are_now_protected(path):
    assert _is_exempt_path(path) is False


@pytest.mark.parametrize(
    "path",
    (
        "/api/oauth/authorize",
        "/api/oauth/callback",
        "/api/storage/yd-file",
        "/api/videos/videos/7",
        "/api/projects/projects/3",
        "/settings/security",
    ),
)
def test_other_paths_are_not_exempt(path):
    """GET-only and normal mutating routes need no exemption."""
    assert _is_exempt_path(path) is False


def test_prefix_lookalikes_are_not_exempt():
    """Exact matching must not be fooled by a path that merely starts alike."""
    assert _is_exempt_path("/api/auth/login-evil") is False
    assert _is_exempt_path("/admin/login-form-extra") is False
    assert _is_exempt_path("/api/oauth/1/create-folder/../../auth/login") is False


def test_no_mutating_route_in_the_application_is_csrf_exempt():
    """Property test over the real route table.

    Adding a new mutating endpoint must not silently join the exempt list.
    """
    from app.main import app
    from app.middleware.csrf import SAFE_METHODS

    spec = app.openapi()
    offenders = []

    for path, operations in spec.get("paths", {}).items():
        mutating = [m for m in operations if m.upper() not in SAFE_METHODS]
        if not mutating:
            continue
        if _is_exempt_path(path) and path.rstrip("/") not in LOGIN_PATHS:
            offenders.append((path, sorted(m.upper() for m in mutating)))

    assert offenders == [], f"mutating routes must not bypass CSRF: {offenders}"


def test_csrf_middleware_is_registered():
    """The exemption list is irrelevant if the middleware is not installed."""
    from app.main import app

    assert any(
        mw.cls is CSRFMiddleware for mw in app.user_middleware
    ), "CSRFMiddleware is not registered on the application"


# ----------------------------------------------------------------------
# Middleware behaviour
# ----------------------------------------------------------------------


def _make_request(
    method: str,
    path: str,
    *,
    cookies: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> Request:
    raw_headers = [
        (k.lower().encode(), v.encode()) for k, v in (headers or {}).items()
    ]
    if cookies:
        cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())
        raw_headers.append((b"cookie", cookie_header.encode()))

    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": raw_headers,
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)


async def _drive(request: Request) -> tuple[Response, bool]:
    """Run the middleware. Returns (response, whether the app was reached)."""
    reached = {"value": False}

    async def call_next(_request):
        reached["value"] = True
        return Response("ok", status_code=200)

    middleware = CSRFMiddleware(app=lambda scope, receive, send: None)
    response = await middleware.dispatch(request, call_next)
    return response, reached["value"]


@pytest.mark.asyncio
async def test_mutating_request_with_cookie_but_no_token_is_rejected():
    request = _make_request(
        "POST",
        "/api/companies/1/yandex-auth-code",
        cookies={"access_token": "jwt"},
        headers={"content-type": "application/json"},
    )

    response, reached = await _drive(request)

    assert response.status_code == 403
    assert reached is False, "the handler must never be reached"


@pytest.mark.asyncio
async def test_mutating_request_with_mismatched_token_is_rejected():
    request = _make_request(
        "DELETE",
        "/api/companies/1/yandex-token",
        cookies={"access_token": "jwt", CSRF_COOKIE_NAME: "correct-token"},
        headers={CSRF_HEADER_NAME: "attacker-token"},
    )

    response, reached = await _drive(request)

    assert response.status_code == 403
    assert reached is False


@pytest.mark.asyncio
async def test_mutating_request_with_matching_token_passes_through():
    request = _make_request(
        "POST",
        "/api/companies/1/yandex-auth-code",
        cookies={"access_token": "jwt", CSRF_COOKIE_NAME: "correct-token"},
        headers={
            "content-type": "application/json",
            CSRF_HEADER_NAME: "correct-token",
        },
    )

    response, reached = await _drive(request)

    assert response.status_code == 200
    assert reached is True


@pytest.mark.asyncio
async def test_create_folder_requires_a_token_now():
    request = _make_request(
        "POST",
        "/api/oauth/1/create-folder",
        cookies={"access_token": "jwt"},
        headers={"content-type": "application/json"},
    )

    response, reached = await _drive(request)

    assert response.status_code == 403
    assert reached is False


@pytest.mark.asyncio
async def test_token_authenticated_api_clients_are_unaffected():
    """No access_token cookie -> no CSRF requirement (Bearer/API/webhook callers)."""
    request = _make_request(
        "POST",
        "/api/companies/1/yandex-auth-code",
        headers={"content-type": "application/json", "authorization": "Bearer x"},
    )

    response, reached = await _drive(request)

    assert response.status_code == 200
    assert reached is True


@pytest.mark.asyncio
async def test_login_endpoint_needs_no_token():
    request = _make_request(
        "POST",
        "/api/auth/login",
        headers={"content-type": "application/json"},
    )

    response, reached = await _drive(request)

    assert response.status_code == 200
    assert reached is True


@pytest.mark.asyncio
async def test_safe_methods_are_never_validated():
    request = _make_request(
        "GET",
        "/api/oauth/1/folders",
        cookies={"access_token": "jwt"},
    )

    response, reached = await _drive(request)

    assert response.status_code == 200
    assert reached is True


# ----------------------------------------------------------------------
# End-to-end through the real ASGI stack
# ----------------------------------------------------------------------


def test_real_app_rejects_cookie_request_without_csrf_token():
    """End-to-end proof that the middleware is active and enforcing.

    The request is rejected before any database access, so no DB is required.
    """
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    response = client.post(
        "/api/companies/1/yandex-auth-code",
        json={"code": "attacker-code"},
        cookies={"access_token": "forged-jwt"},
    )

    assert response.status_code == 403
    assert "CSRF" in response.text


def test_real_app_allows_login_without_csrf_token():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    response = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "wrong"},
    )

    # Reaches the handler: 401 for bad credentials, never a CSRF rejection.
    assert response.status_code != 403 or "CSRF" not in response.text
