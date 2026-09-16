import pytest


class _DummyUser:
    # Global settings are super-admin only (ARV-001).
    is_active = True
    is_super_admin = True
    company_id = None
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


@pytest.mark.asyncio
async def test_backup_settings_persists_the_gfs_ladder(monkeypatch):
    """A tuned ladder must survive the round-trip through the form.

    Regression guard: the route used to build ``BackupSettings(...)`` without
    the ``backup_keep_*`` fields, so every save silently rewrote the stored
    ladder back to the schema defaults (7/4/12/3).
    """
    import httpx
    from fastapi.responses import HTMLResponse

    from app.api.routes.auth import get_current_user_optional
    from app.html.deps import get_html_db
    from app.html.routes import settings as settings_routes
    from app.main import app

    captured = {}

    async def fake_user():
        return _DummyUser()

    async def fake_db():
        yield None

    async def fake_render_settings(*args, **kwargs):
        return HTMLResponse("backup-ok", status_code=200)

    async def fake_update_backup_settings(self, payload):
        captured["payload"] = payload
        return payload

    def fake_reschedule(*args, **kwargs):
        captured["rescheduled"] = (args, kwargs)

    app.dependency_overrides[get_current_user_optional] = fake_user
    app.dependency_overrides[get_html_db] = fake_db
    monkeypatch.setattr(settings_routes, "_render_settings", fake_render_settings)
    monkeypatch.setattr(
        settings_routes.SettingsService, "update_backup_settings", fake_update_backup_settings
    )
    monkeypatch.setattr("app.core.scheduler.reschedule_backup", fake_reschedule)

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            client.cookies.set("access_token", "dummy")
            client.cookies.set("csrf_token", "csrf-test-token")
            response = await client.post(
                "/settings/backup",
                headers={"X-CSRF-Token": "csrf-test-token"},
                data={
                    "backup_enabled": "on",
                    "backup_company_id": "7",
                    "backup_yd_folder": "backups",
                    "backup_schedule": "custom",
                    "backup_cron": "0 4 * * *",
                    "backup_retention_days": "45",
                    "backup_max_copies": "20",
                    "backup_keep_daily": "10",
                    "backup_keep_weekly": "6",
                    "backup_keep_monthly": "18",
                    "backup_keep_yearly": "5",
                },
            )
    finally:
        app.dependency_overrides.pop(get_current_user_optional, None)
        app.dependency_overrides.pop(get_html_db, None)

    assert response.status_code == 200
    payload = captured["payload"]
    assert payload.backup_keep_daily == 10
    assert payload.backup_keep_weekly == 6
    assert payload.backup_keep_monthly == 18
    assert payload.backup_keep_yearly == 5
    # The legacy knobs still round-trip so a save does not rewrite them.
    assert payload.backup_retention_days == 45
    assert payload.backup_max_copies == 20
    assert payload.backup_cron == "0 4 * * *"


@pytest.mark.asyncio
async def test_backup_settings_refuses_an_all_zero_ladder(monkeypatch):
    """All-zero means "delete every backup", so it must be rejected outright."""
    import httpx
    from fastapi.responses import HTMLResponse

    from app.api.routes.auth import get_current_user_optional
    from app.html.deps import get_html_db
    from app.html.routes import settings as settings_routes
    from app.main import app

    called = {"update": False}

    async def fake_user():
        return _DummyUser()

    async def fake_db():
        yield None

    async def fake_render_settings(*args, **kwargs):
        return HTMLResponse(f"err:{kwargs.get('error_message')}", status_code=200)

    async def fake_update_backup_settings(self, payload):
        called["update"] = True

    app.dependency_overrides[get_current_user_optional] = fake_user
    app.dependency_overrides[get_html_db] = fake_db
    monkeypatch.setattr(settings_routes, "_render_settings", fake_render_settings)
    monkeypatch.setattr(
        settings_routes.SettingsService, "update_backup_settings", fake_update_backup_settings
    )

    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            client.cookies.set("access_token", "dummy")
            client.cookies.set("csrf_token", "csrf-test-token")
            response = await client.post(
                "/settings/backup",
                headers={"X-CSRF-Token": "csrf-test-token"},
                data={
                    "backup_enabled": "on",
                    "backup_company_id": "7",
                    "backup_yd_folder": "backups",
                    "backup_schedule": "daily",
                    "backup_cron": "0 3 * * *",
                    "backup_retention_days": "30",
                    "backup_max_copies": "30",
                    "backup_keep_daily": "0",
                    "backup_keep_weekly": "0",
                    "backup_keep_monthly": "0",
                    "backup_keep_yearly": "0",
                },
            )
    finally:
        app.dependency_overrides.pop(get_current_user_optional, None)
        app.dependency_overrides.pop(get_html_db, None)

    assert response.status_code == 200
    assert called["update"] is False, "an all-zero ladder must not reach the settings service"
    assert "err:" in response.text
    assert response.text.strip() != "err:None"
