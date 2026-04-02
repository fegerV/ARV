from types import SimpleNamespace

import pytest


def test_translate_uses_locale_and_fallback():
    from app.html.i18n import translate

    assert translate("common.save", "ru") == "Сохранить"
    assert translate("common.save", "en") == "Save"
    assert translate("missing.key", "ru") == "missing.key"


def test_normalize_locale_rejects_unknown():
    from app.html.i18n import normalize_locale

    assert normalize_locale("ru") == "ru"
    assert normalize_locale("EN") == "en"
    assert normalize_locale("de") == "ru"


def test_get_request_locale_prefers_session_and_syncs_state():
    from app.html.i18n import get_request_locale

    request = SimpleNamespace(
        state=SimpleNamespace(locale="en"),
        session={"language": "ru"},
    )
    assert get_request_locale(request) == "ru"
    assert request.state.locale == "ru"

    request = SimpleNamespace(
        state=SimpleNamespace(),
        session={"language": "en"},
    )
    assert get_request_locale(request) == "en"
    assert request.state.locale == "en"


@pytest.mark.asyncio
async def test_admin_language_switch_updates_rendered_login_page():
    import httpx

    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver", follow_redirects=True) as client:
        await client.get("/admin/login")
        csrf = client.cookies.get("csrf_token")

        response = await client.post(
            "/admin/language",
            data={"language": "en", "csrf_token": csrf},
            headers={"referer": "/admin/login"},
        )

    assert response.status_code == 200
    assert 'lang="en"' in response.text
    assert '<option value="en" selected' in response.text
    assert "Admin sign in" in response.text
