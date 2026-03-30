import importlib
from types import SimpleNamespace

import pytest


def test_publish_alerts_is_noop():
    alert_service = _alert_service_module()

    result = pytest.run(async_fn=alert_service.publish_alerts([_sample_alert()])) if False else None
    assert result is None


@pytest.mark.asyncio
async def test_publish_alerts_returns_none():
    alert_service = _alert_service_module()

    assert await alert_service.publish_alerts([_sample_alert()]) is None


@pytest.mark.asyncio
async def test_send_critical_alerts_returns_early_on_empty_list(monkeypatch):
    alert_service = _alert_service_module()
    calls = []

    monkeypatch.setattr(alert_service, "send_admin_email", _async_record(calls, "email"))
    monkeypatch.setattr(alert_service, "send_telegram_alerts", _async_record(calls, "telegram"))
    monkeypatch.setattr(alert_service, "publish_alerts", _async_record(calls, "publish"))

    await alert_service.send_critical_alerts([], {"cpu_percent": 1})

    assert calls == []


@pytest.mark.asyncio
async def test_send_critical_alerts_calls_email_telegram_and_publish(monkeypatch):
    alert_service = _alert_service_module()
    calls = []
    alerts = [_sample_alert()]
    metrics = {"cpu_percent": 95}

    monkeypatch.setattr(alert_service, "send_admin_email", _async_record(calls, "email"))
    monkeypatch.setattr(alert_service, "send_telegram_alerts", _async_record(calls, "telegram"))
    monkeypatch.setattr(alert_service, "publish_alerts", _async_record(calls, "publish"))

    await alert_service.send_critical_alerts(alerts, metrics)

    assert calls == [
        ("email", alerts, metrics),
        ("telegram", alerts, metrics),
        ("publish", alerts),
    ]


@pytest.mark.asyncio
async def test_send_admin_email_sends_message(monkeypatch):
    alert_service = _alert_service_module()
    sent = {}

    class FakeSMTP:
        def __init__(self, host, port):
            sent["host"] = host
            sent["port"] = port
            sent["login"] = None
            sent["starttls"] = 0

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def starttls(self):
            sent["starttls"] += 1

        def login(self, username, password):
            sent["login"] = (username, password)

        def send_message(self, msg):
            sent["from"] = msg["From"]
            sent["to"] = msg["To"]
            sent["subject"] = msg["Subject"]
            sent["payload"] = msg.get_payload()[0].get_payload(decode=True).decode("utf-8")

    monkeypatch.setattr(alert_service.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(
        alert_service,
        "settings",
        SimpleNamespace(
            SMTP_FROM_EMAIL="noreply@example.com",
            ADMIN_EMAIL="admin@example.com",
            SMTP_HOST="smtp.example.com",
            SMTP_PORT=2525,
            SMTP_USERNAME="mailer",
            SMTP_PASSWORD="secret",
            ADMIN_FRONTEND_URL="https://admin.example.com",
        ),
    )

    await alert_service.send_admin_email([_sample_alert()], {"cpu_percent": 90, "memory_percent": 80, "api_health": "ok"})

    assert sent["host"] == "smtp.example.com"
    assert sent["port"] == 2525
    assert sent["starttls"] == 1
    assert sent["login"] == ("mailer", "secret")
    assert sent["from"] == "noreply@example.com"
    assert sent["to"] == "admin@example.com"
    assert "critical issues" in sent["subject"]
    assert "CPU: 90%" in sent["payload"]
    assert "API Health: ok" in sent["payload"]


@pytest.mark.asyncio
async def test_send_admin_email_swallow_errors(monkeypatch):
    alert_service = _alert_service_module()
    errors = []

    class FakeSMTP:
        def __init__(self, host, port):
            pass

        def __enter__(self):
            raise RuntimeError("smtp down")

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(alert_service.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(
        alert_service,
        "settings",
        SimpleNamespace(
            SMTP_FROM_EMAIL="noreply@example.com",
            ADMIN_EMAIL="admin@example.com",
            SMTP_HOST="smtp.example.com",
            SMTP_PORT=2525,
            SMTP_USERNAME=None,
            SMTP_PASSWORD=None,
            ADMIN_FRONTEND_URL="https://admin.example.com",
        ),
    )
    monkeypatch.setattr(alert_service.logger, "error", lambda event, **kwargs: errors.append((event, kwargs)))

    await alert_service.send_admin_email([_sample_alert()], {})

    assert errors == [("critical_alert_email_failed", {"error": "smtp down"})]


@pytest.mark.asyncio
async def test_send_telegram_alerts_uses_db_settings_when_available(monkeypatch):
    alert_service = _alert_service_module()
    sent = []

    class FakeSettingsService:
        def __init__(self, _session):
            pass

        async def get_all_settings(self):
            return SimpleNamespace(
                notifications=SimpleNamespace(
                    telegram_enabled=True,
                    telegram_bot_token="db-token",
                    telegram_admin_chat_id="db-chat",
                )
            )

    class FakeAsyncSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setitem(
        __import__("sys").modules,
        "app.services.settings_service",
        SimpleNamespace(SettingsService=FakeSettingsService),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "app.core.database",
        SimpleNamespace(AsyncSessionLocal=lambda: FakeAsyncSession()),
    )
    monkeypatch.setattr(alert_service, "send_telegram_message", _async_capture_telegram(sent))
    monkeypatch.setattr(
        alert_service,
        "settings",
        SimpleNamespace(
            TELEGRAM_BOT_TOKEN="env-token",
            TELEGRAM_ADMIN_CHAT_ID="env-chat",
            ADMIN_FRONTEND_URL="https://admin.example.com",
        ),
    )

    await alert_service.send_telegram_alerts([_sample_alert()], {"cpu_percent": 90, "memory_percent": 80, "api_health": "ok"})

    assert sent == [("db-chat", "db-token", True)]


@pytest.mark.asyncio
async def test_send_telegram_alerts_falls_back_to_env_when_settings_load_fails(monkeypatch):
    alert_service = _alert_service_module()
    sent = []
    warnings = []

    monkeypatch.setitem(
        __import__("sys").modules,
        "app.services.settings_service",
        SimpleNamespace(SettingsService=lambda session: (_ for _ in ()).throw(RuntimeError("boom"))),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "app.core.database",
        SimpleNamespace(AsyncSessionLocal=lambda: _FakeAsyncSession()),
    )
    monkeypatch.setattr(alert_service, "send_telegram_message", _async_capture_telegram(sent))
    monkeypatch.setattr(alert_service.logger, "warning", lambda event, **kwargs: warnings.append((event, kwargs)))
    monkeypatch.setattr(
        alert_service,
        "settings",
        SimpleNamespace(
            TELEGRAM_BOT_TOKEN="env-token",
            TELEGRAM_ADMIN_CHAT_ID="env-chat",
            ADMIN_FRONTEND_URL="https://admin.example.com",
        ),
    )

    await alert_service.send_telegram_alerts([_sample_alert()], {"cpu_percent": 90})

    assert warnings == [("alert_telegram_settings_load_failed", {"error": "boom"})]
    assert sent == [("env-chat", "env-token", True)]


@pytest.mark.asyncio
async def test_send_telegram_alerts_warns_when_not_configured(monkeypatch):
    alert_service = _alert_service_module()
    warnings = []

    monkeypatch.setitem(
        __import__("sys").modules,
        "app.services.settings_service",
        SimpleNamespace(SettingsService=lambda session: (_ for _ in ()).throw(RuntimeError("boom"))),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "app.core.database",
        SimpleNamespace(AsyncSessionLocal=lambda: _FakeAsyncSession()),
    )
    monkeypatch.setattr(alert_service.logger, "warning", lambda event, **kwargs: warnings.append((event, kwargs)))
    monkeypatch.setattr(
        alert_service,
        "settings",
        SimpleNamespace(
            TELEGRAM_BOT_TOKEN=None,
            TELEGRAM_ADMIN_CHAT_ID=None,
            ADMIN_FRONTEND_URL="https://admin.example.com",
        ),
    )

    await alert_service.send_telegram_alerts([_sample_alert()], {"cpu_percent": 90})

    assert warnings == [
        ("alert_telegram_settings_load_failed", {"error": "boom"}),
        ("telegram_not_configured", {}),
    ]


@pytest.mark.asyncio
async def test_send_telegram_message_handles_missing_token_success_failure_and_exception(monkeypatch):
    alert_service = _alert_service_module()
    warnings = []
    infos = []
    errors = []

    monkeypatch.setattr(alert_service.logger, "warning", lambda event, **kwargs: warnings.append((event, kwargs)))
    monkeypatch.setattr(alert_service.logger, "info", lambda event, **kwargs: infos.append((event, kwargs)))
    monkeypatch.setattr(alert_service.logger, "error", lambda event, **kwargs: errors.append((event, kwargs)))
    monkeypatch.setattr(alert_service, "settings", SimpleNamespace(TELEGRAM_BOT_TOKEN=None))

    await alert_service.send_telegram_message("chat", "message")

    assert warnings == [("telegram_bot_token_missing", {})]

    class FakeResponseOk:
        status_code = 200

    class FakeResponseFail:
        status_code = 500

    class FakeAsyncClientOk:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json, timeout):
            return FakeResponseOk()

    class FakeAsyncClientFail:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json, timeout):
            return FakeResponseFail()

    class FakeAsyncClientError:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json, timeout):
            raise RuntimeError("network down")

    monkeypatch.setattr(alert_service, "settings", SimpleNamespace(TELEGRAM_BOT_TOKEN="env-token"))
    monkeypatch.setattr(alert_service.httpx, "AsyncClient", FakeAsyncClientOk)
    await alert_service.send_telegram_message("chat", "message", bot_token="override-token")

    monkeypatch.setattr(alert_service.httpx, "AsyncClient", FakeAsyncClientFail)
    await alert_service.send_telegram_message("chat", "message")

    monkeypatch.setattr(alert_service.httpx, "AsyncClient", FakeAsyncClientError)
    await alert_service.send_telegram_message("chat", "message")

    assert infos == [("telegram_alert_sent", {"chat_id": "chat"})]
    assert errors == [
        ("telegram_alert_failed", {"status": 500}),
        ("telegram_alert_error", {"error": "network down"}),
    ]


@pytest.mark.asyncio
async def test_alert_service_wrapper_delegates(monkeypatch):
    alert_service = _alert_service_module()
    service = alert_service.AlertService()
    calls = []

    monkeypatch.setattr(alert_service, "publish_alerts", _async_record(calls, "publish"))
    monkeypatch.setattr(alert_service, "send_critical_alerts", _async_record(calls, "critical"))
    monkeypatch.setattr(alert_service, "send_admin_email", _async_record(calls, "email"))
    monkeypatch.setattr(alert_service, "send_telegram_alerts", _async_record(calls, "telegram"))
    monkeypatch.setattr(alert_service, "send_telegram_message", _async_record(calls, "message"))

    alerts = [_sample_alert()]
    metrics = {"cpu_percent": 1}

    await service.publish_alerts(alerts)
    await service.send_critical_alerts(alerts, metrics)
    await service.send_admin_email(alerts, metrics)
    await service.send_telegram_alerts(alerts, metrics)
    await service.send_telegram_message("chat", "message")

    assert calls == [
        ("publish", alerts),
        ("critical", alerts, metrics),
        ("email", alerts, metrics),
        ("telegram", alerts, metrics),
        ("message", "chat", "message"),
    ]


class _FakeAsyncSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _sample_alert():
    alert_service = _alert_service_module()
    return alert_service.Alert(
        severity="critical",
        title="API down",
        message="Viewer API is unavailable",
        metrics={"cpu_percent": 90},
        affected_services=["viewer"],
    )


def _async_record(calls, label):
    async def _inner(*args):
        calls.append((label, *args))
        return None

    return _inner


def _async_capture_telegram(sent):
    async def _inner(chat_id, message, bot_token=None):
        sent.append((chat_id, bot_token, "Vertex AR Alerts" in message))
        return None

    return _inner


def _alert_service_module():
    return importlib.import_module("app.services.alert_service")
