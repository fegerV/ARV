from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Request, Response
from fastapi.security import OAuth2PasswordRequestForm


def test_extract_request_token_prefers_explicit_header_then_cookie():
    from app.api.routes.auth import _extract_request_token

    request = _make_request(
        headers={"Authorization": "Bearer header-token"},
        cookies={"access_token": "cookie-token"},
    )

    assert _extract_request_token(request, "explicit-token") == "explicit-token"
    assert _extract_request_token(request) == "header-token"
    assert _extract_request_token(_make_request(cookies={"access_token": "cookie-token"})) == "cookie-token"
    assert _extract_request_token(_make_request()) is None


@pytest.mark.asyncio
async def test_get_user_from_token_returns_none_for_missing_or_invalid_token(monkeypatch):
    from app.api.routes.auth import _get_user_from_token
    from app.api.routes import auth

    monkeypatch.setattr(auth, "decode_token", lambda token: None)

    assert await _get_user_from_token(_FakeDb(), None) is None
    assert await _get_user_from_token(_FakeDb(), "bad-token") is None


@pytest.mark.asyncio
async def test_get_user_from_token_loads_user_by_email(monkeypatch):
    from app.api.routes.auth import _get_user_from_token
    from app.api.routes import auth

    user = SimpleNamespace(id=7, email="admin@example.com")
    monkeypatch.setattr(auth, "decode_token", lambda token: {"sub": "admin@example.com"})

    db = _FakeDb(execute_results=[_FakeScalarOneOrNoneResult(user)])

    result = await _get_user_from_token(db, "good-token")

    assert result is user


@pytest.mark.asyncio
async def test_get_current_user_raises_for_missing_credentials():
    from app.api.routes.auth import get_current_user

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request=_make_request(), db=_FakeDb())

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"


@pytest.mark.asyncio
async def test_get_current_active_user_requires_active_user(monkeypatch):
    from app.api.routes import auth

    async def _inactive_user(_db, _token):
        return SimpleNamespace(is_active=False)

    monkeypatch.setattr(auth, "_get_user_from_token", _inactive_user)

    with pytest.raises(HTTPException) as exc_info:
        await auth.get_current_active_user(request=_make_request(), db=_FakeDb())

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Inactive user or not authenticated"


@pytest.mark.asyncio
async def test_get_session_timeout_minutes_falls_back_on_service_error(monkeypatch):
    from app.api.routes import auth

    monkeypatch.setattr(auth, "get_settings", lambda: SimpleNamespace(ACCESS_TOKEN_EXPIRE_MINUTES=45))
    monkeypatch.setitem(
        __import__("sys").modules,
        "app.services.settings_service",
        SimpleNamespace(SettingsService=lambda db: (_ for _ in ()).throw(RuntimeError("boom"))),
    )

    result = await auth.get_session_timeout_minutes(_FakeDb())

    assert result == 45


def test_auth_cookie_helpers_set_and_clear_values(monkeypatch):
    from app.api.routes import auth

    monkeypatch.setattr(auth, "get_settings", lambda: SimpleNamespace(is_production=False))

    response = Response()
    auth.create_access_token_cookie(response, "token-123", 5)
    auth.clear_auth_cookies(response)

    set_cookie_headers = "\n".join(response.headers.getlist("set-cookie"))
    assert "access_token=token-123" in set_cookie_headers
    assert "Max-Age=300" in set_cookie_headers
    assert "csrf_token=\"\"" in set_cookie_headers


@pytest.mark.asyncio
async def test_login_returns_token_and_resets_attempts(monkeypatch):
    from app.api.routes import auth

    user = SimpleNamespace(
        id=1,
        email="admin@example.com",
        full_name="Admin",
        role="admin",
        hashed_password="legacy-hash",
        is_active=True,
        login_attempts=3,
        locked_until=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1),
        last_login_at=None,
    )

    monkeypatch.setattr(auth, "verify_password", lambda raw, hashed: True)
    monkeypatch.setattr(auth, "needs_password_rehash", lambda hashed: True)
    monkeypatch.setattr(auth, "get_password_hash", lambda raw: "rehashed")
    monkeypatch.setattr(auth, "create_access_token", lambda data, expires_delta: "jwt-token")
    monkeypatch.setattr(auth, "get_session_timeout_minutes", _async_return(30))

    db = _FakeDb(execute_results=[_FakeScalarOneOrNoneResult(user)])

    result = await auth.login(
        request=_make_request(),
        form_data=OAuth2PasswordRequestForm(username="admin@example.com", password="secret", scope=""),
        db=db,
    )

    assert result["access_token"] == "jwt-token"
    assert result["token_type"] == "bearer"
    assert result["user"].email == "admin@example.com"
    assert user.login_attempts == 0
    assert user.locked_until is None
    assert user.hashed_password == "rehashed"
    assert user.last_login_at is not None
    assert db.commit_calls >= 1


@pytest.mark.asyncio
async def test_login_locks_account_after_max_attempts(monkeypatch):
    from app.api.routes import auth

    user = SimpleNamespace(
        id=2,
        email="admin@example.com",
        hashed_password="stored-hash",
        is_active=True,
        login_attempts=4,
        locked_until=None,
    )

    monkeypatch.setattr(auth, "verify_password", lambda raw, hashed: False)

    db = _FakeDb(execute_results=[_FakeScalarOneOrNoneResult(user)])

    with pytest.raises(HTTPException) as exc_info:
        await auth.login(
            request=_make_request(),
            form_data=OAuth2PasswordRequestForm(username="admin@example.com", password="bad", scope=""),
            db=db,
        )

    assert exc_info.value.status_code == 403
    assert user.login_attempts == 5
    assert user.locked_until is not None
    assert db.commit_calls == 1


@pytest.mark.asyncio
async def test_register_user_requires_admin_role():
    from app.api.routes import auth

    with pytest.raises(HTTPException) as exc_info:
        await auth.register_user(
            request=_make_request(),
            user_data=auth.RegisterRequest(
                email="new@example.com",
                password="Password123",
                full_name="New User",
                role="editor",
            ),
            db=_FakeDb(),
            current_user=SimpleNamespace(id=1, email="user@example.com", role="editor"),
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Only administrators can create new users"


@pytest.mark.asyncio
async def test_register_user_rejects_duplicate_email():
    from app.api.routes import auth

    db = _FakeDb(execute_results=[_FakeScalarOneOrNoneResult(SimpleNamespace(id=9, email="new@example.com"))])

    with pytest.raises(HTTPException) as exc_info:
        await auth.register_user(
            request=_make_request(),
            user_data=auth.RegisterRequest(
                email="new@example.com",
                password="Password123",
                full_name="New User",
            ),
            db=db,
            current_user=SimpleNamespace(id=1, email="admin@example.com", role="admin"),
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Email already registered"


@pytest.mark.asyncio
async def test_register_user_creates_new_user(monkeypatch):
    from app.api.routes import auth

    monkeypatch.setattr(auth, "get_password_hash", lambda password: "hashed-password")

    db = _FakeDb(execute_results=[_FakeScalarOneOrNoneResult(None)])

    result = await auth.register_user(
        request=_make_request(),
        user_data=auth.RegisterRequest(
            email="new@example.com",
            password="Password123",
            full_name="New User",
            role="admin",
        ),
        db=db,
        current_user=SimpleNamespace(id=1, email="admin@example.com", role="admin"),
    )

    assert db.added is not None
    assert db.added.email == "new@example.com"
    assert db.added.hashed_password == "hashed-password"
    assert db.commit_calls == 1
    assert db.refresh_calls == 1
    assert result.user.email == "new@example.com"


def _make_request(headers=None, cookies=None):
    scope = {
        "type": "http",
        "path": "/api/auth/login",
        "method": "POST",
        "client": ("127.0.0.1", 50000),
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
    }
    request = Request(scope)
    request._cookies = cookies or {}
    return request


def _async_return(value):
    async def _inner(*args, **kwargs):
        return value

    return _inner


class _FakeScalarOneOrNoneResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeDb:
    def __init__(self, execute_results=None):
        self.execute_results = list(execute_results or [])
        self.added = None
        self.commit_calls = 0
        self.refresh_calls = 0

    async def execute(self, _stmt):
        return self.execute_results.pop(0)

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = 401
        self.added = obj

    async def commit(self):
        self.commit_calls += 1

    async def refresh(self, _obj):
        self.refresh_calls += 1
