import pytest


class _DummyUser:
    is_active = True
    email = "admin@vertexar.com"


@pytest.mark.asyncio
async def test_general_settings_accepts_header_csrf(monkeypatch):
    import httpx
    from fastapi.responses import HTMLResponse

    from app.api.routes.auth import get_current_user_optional
    from app.html.deps import get_html_db
    from app.html.routes import settings as settings_routes
    from app.main import app

    async def fake_user():
        return _DummyUser()

    async def fake_db():
        yield None

    async def fake_render_settings(*args, **kwargs):
        return HTMLResponse("general-ok", status_code=200)

    async def fake_update_general_settings(self, payload):
        assert payload.site_title == "Vertex AR B2B Platform"
        assert payload.admin_email == "admin@vertexar.com"
        assert payload.site_description

    app.dependency_overrides[get_current_user_optional] = fake_user
    app.dependency_overrides[get_html_db] = fake_db
    monkeypatch.setattr(settings_routes, "_render_settings", fake_render_settings)
    monkeypatch.setattr(settings_routes.SettingsService, "update_general_settings", fake_update_general_settings)

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            client.cookies.set("access_token", "dummy")
            client.cookies.set("csrf_token", "csrf-test-token")
            response = await client.post(
                "/settings/general",
                headers={"X-CSRF-Token": "csrf-test-token"},
                data={
                    "site_title": "Vertex AR B2B Platform",
                    "admin_email": "admin@vertexar.com",
                    "site_description": "B2B SaaS platform",
                    "timezone": "Europe/Moscow",
                    "language": "ru",
                    "default_subscription_years": "30",
                },
            )
    finally:
        app.dependency_overrides.pop(get_current_user_optional, None)
        app.dependency_overrides.pop(get_html_db, None)

    assert response.status_code == 200
    assert "general-ok" in response.text


@pytest.mark.asyncio
async def test_security_settings_accepts_header_csrf(monkeypatch):
    import httpx
    from fastapi.responses import HTMLResponse

    from app.api.routes.auth import get_current_user_optional
    from app.html.deps import get_html_db
    from app.html.routes import settings as settings_routes
    from app.main import app

    async def fake_user():
        return _DummyUser()

    async def fake_db():
        yield None

    async def fake_render_settings(*args, **kwargs):
        return HTMLResponse("security-ok", status_code=200)

    async def fake_update_security_settings(self, payload):
        assert payload.password_min_length == 8
        assert payload.session_timeout == 60
        assert payload.api_rate_limit == 100

    app.dependency_overrides[get_current_user_optional] = fake_user
    app.dependency_overrides[get_html_db] = fake_db
    monkeypatch.setattr(settings_routes, "_render_settings", fake_render_settings)
    monkeypatch.setattr(settings_routes.SettingsService, "update_security_settings", fake_update_security_settings)

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            client.cookies.set("access_token", "dummy")
            client.cookies.set("csrf_token", "csrf-test-token")
            response = await client.post(
                "/settings/security",
                headers={"X-CSRF-Token": "csrf-test-token"},
                data={
                    "password_min_length": "8",
                    "session_timeout": "60",
                    "max_login_attempts": "5",
                    "lockout_duration": "300",
                    "api_rate_limit": "100",
                    "telegram_2fa_chat_id": "",
                },
            )
    finally:
        app.dependency_overrides.pop(get_current_user_optional, None)
        app.dependency_overrides.pop(get_html_db, None)

    assert response.status_code == 200
    assert "security-ok" in response.text
