from types import SimpleNamespace


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


def test_get_request_locale_prefers_state_then_session():
    from app.html.i18n import get_request_locale

    request = SimpleNamespace(
        state=SimpleNamespace(locale="en"),
        session={"language": "ru"},
    )
    assert get_request_locale(request) == "en"

    request = SimpleNamespace(
        state=SimpleNamespace(),
        session={"language": "en"},
    )
    assert get_request_locale(request) == "en"
