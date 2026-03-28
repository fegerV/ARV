import hashlib

import pytest


def test_password_hash_uses_pbkdf2_and_verifies():
    from app.core.security import get_password_hash, verify_password, needs_password_rehash

    hashed = get_password_hash("Secret123!")
    assert hashed.startswith("$pbkdf2-sha256$")
    assert verify_password("Secret123!", hashed) is True
    assert verify_password("wrong", hashed) is False
    assert needs_password_rehash(hashed) is False


def test_legacy_sha256_hash_still_verifies_but_requires_upgrade():
    from app.core.security import verify_password, needs_password_rehash

    legacy_hash = hashlib.sha256("Secret123!".encode()).hexdigest()
    assert verify_password("Secret123!", legacy_hash) is True
    assert verify_password("wrong", legacy_hash) is False
    assert needs_password_rehash(legacy_hash) is True


@pytest.mark.asyncio
async def test_csrf_blocks_cookie_authenticated_post_without_token():
    import httpx
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver", follow_redirects=False) as client:
        client.cookies.set("access_token", "dummy")
        response = await client.post("/admin/logout")
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_logout_accepts_matching_csrf_token():
    import httpx
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver", follow_redirects=False) as client:
        client.cookies.set("access_token", "dummy")
        client.cookies.set("csrf_token", "csrf-test-token")
        response = await client.post("/admin/logout", data={"csrf_token": "csrf-test-token"})
        assert response.status_code == 303
        assert response.headers["location"] == "/admin/login"
        set_cookie = "\n".join(response.headers.get_list("set-cookie"))
        assert "access_token=\"\"" in set_cookie
        assert "csrf_token=\"\"" in set_cookie


@pytest.mark.asyncio
async def test_api_logout_clears_auth_cookies(monkeypatch):
    import httpx
    from app.main import app
    from app.api.routes import auth as auth_routes

    async def fake_current_user():
        class DummyUser:
            id = 1
            email = "admin@example.com"

        return DummyUser()

    app.dependency_overrides[auth_routes.get_current_active_user] = fake_current_user
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver", follow_redirects=False) as client:
            client.cookies.set("access_token", "dummy")
            client.cookies.set("csrf_token", "csrf-test-token")
            response = await client.post("/api/auth/logout", headers={"X-CSRF-Token": "csrf-test-token"})
            assert response.status_code == 200
            set_cookie = "\n".join(response.headers.get_list("set-cookie"))
            assert "access_token=\"\"" in set_cookie
            assert "csrf_token=\"\"" in set_cookie
    finally:
        app.dependency_overrides.pop(auth_routes.get_current_active_user, None)
