import importlib
from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_create_notification_persists_and_refreshes_record():
    notification_service = _notification_service_module()

    session = _FakeSession()

    result = await notification_service.create_notification(
        session,
        notification_type="project_expiring",
        subject="Soon",
        message="Project will expire",
        company_id=7,
        project_id=8,
        ar_content_id=9,
        metadata={"severity": "warning"},
    )

    assert result is session.added[0]
    assert result.notification_type == "project_expiring"
    assert result.subject == "Soon"
    assert result.message == "Project will expire"
    assert result.company_id == 7
    assert result.project_id == 8
    assert result.ar_content_id == 9
    assert result.notification_metadata == {"severity": "warning"}
    assert result.created_at is not None
    assert session.flush_calls == 1
    assert session.commit_calls == 1
    assert session.refresh_calls == [result]
    assert session.rollback_calls == 0


@pytest.mark.asyncio
async def test_create_notification_rolls_back_on_error():
    notification_service = _notification_service_module()

    session = _FakeSession(fail_on_flush=True)

    with pytest.raises(RuntimeError, match="db flush failed"):
        await notification_service.create_notification(
            session,
            notification_type="project_expiring",
            subject="Soon",
            message="Project will expire",
        )

    assert session.rollback_calls == 1
    assert session.commit_calls == 0
    assert session.refresh_calls == []


def test_send_expiry_warning_email_sends_message_with_optional_login(monkeypatch):
    notification_service = _notification_service_module()

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

    monkeypatch.setattr(notification_service.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(
        notification_service,
        "settings",
        SimpleNamespace(
            SMTP_FROM_EMAIL="noreply@example.com",
            SMTP_HOST="smtp.example.com",
            SMTP_PORT=2525,
            SMTP_USERNAME="mailer",
            SMTP_PASSWORD="secret",
            TELEGRAM_BOT_TOKEN="telegram-token",
        ),
    )

    result = notification_service.send_expiry_warning_email(
        "Vertex Demo",
        "client@example.com",
        "2026-04-01",
        3,
    )

    assert result is True
    assert sent["host"] == "smtp.example.com"
    assert sent["port"] == 2525
    assert sent["starttls"] == 1
    assert sent["login"] == ("mailer", "secret")
    assert sent["from"] == "noreply@example.com"
    assert sent["to"] == "client@example.com"
    assert "Vertex Demo" in sent["subject"]


def test_send_expiry_warning_email_returns_false_on_smtp_error(monkeypatch):
    notification_service = _notification_service_module()

    class FakeSMTP:
        def __init__(self, host, port):
            pass

        def __enter__(self):
            raise RuntimeError("smtp down")

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(notification_service.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(
        notification_service,
        "settings",
        SimpleNamespace(
            SMTP_FROM_EMAIL="noreply@example.com",
            SMTP_HOST="smtp.example.com",
            SMTP_PORT=2525,
            SMTP_USERNAME=None,
            SMTP_PASSWORD=None,
            TELEGRAM_BOT_TOKEN="telegram-token",
        ),
    )

    result = notification_service.send_expiry_warning_email(
        "Vertex Demo",
        "client@example.com",
        "2026-04-01",
        3,
    )

    assert result is False


@pytest.mark.asyncio
async def test_send_expiry_warning_telegram_returns_true_on_200(monkeypatch):
    notification_service = _notification_service_module()

    captured = {}

    class FakeResponse:
        status_code = 200

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json):
            captured["url"] = url
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr(notification_service.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(
        notification_service,
        "settings",
        SimpleNamespace(TELEGRAM_BOT_TOKEN="telegram-token"),
    )

    result = await notification_service.send_expiry_warning_telegram(
        "12345",
        "Vertex Demo",
        "2026-04-01",
        3,
    )

    assert result is True
    assert captured["url"] == "https://api.telegram.org/bottelegram-token/sendMessage"
    assert captured["json"]["chat_id"] == "12345"
    assert captured["json"]["parse_mode"] == "HTML"
    assert "Vertex Demo" in captured["json"]["text"]


@pytest.mark.asyncio
async def test_send_expiry_warning_telegram_returns_false_on_non_200(monkeypatch):
    notification_service = _notification_service_module()

    class FakeResponse:
        status_code = 500

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json):
            return FakeResponse()

    monkeypatch.setattr(notification_service.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(
        notification_service,
        "settings",
        SimpleNamespace(TELEGRAM_BOT_TOKEN="telegram-token"),
    )

    result = await notification_service.send_expiry_warning_telegram(
        "12345",
        "Vertex Demo",
        "2026-04-01",
        3,
    )

    assert result is False


@pytest.mark.asyncio
async def test_send_expiry_warning_telegram_returns_false_on_exception(monkeypatch):
    notification_service = _notification_service_module()

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json):
            raise RuntimeError("network down")

    monkeypatch.setattr(notification_service.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(
        notification_service,
        "settings",
        SimpleNamespace(TELEGRAM_BOT_TOKEN="telegram-token"),
    )

    result = await notification_service.send_expiry_warning_telegram(
        "12345",
        "Vertex Demo",
        "2026-04-01",
        3,
    )

    assert result is False


@pytest.mark.asyncio
async def test_notification_service_wrapper_delegates(monkeypatch):
    notification_service_module = _notification_service_module()
    NotificationService = notification_service_module.NotificationService

    service = NotificationService()
    session = _FakeSession()
    created = SimpleNamespace(id=1)

    async def _fake_create_notification(*args, **kwargs):
        assert args[:4] == (session, "type", "subject", "message")
        return created

    async def _fake_send_expiry_warning_telegram(*args, **kwargs):
        assert args == ("chat", "project", "2026-04-01", 2)
        return True

    monkeypatch.setattr(notification_service_module, "create_notification", _fake_create_notification)
    monkeypatch.setattr(notification_service_module, "send_expiry_warning_email", lambda *args: True)
    monkeypatch.setattr(notification_service_module, "send_expiry_warning_telegram", _fake_send_expiry_warning_telegram)

    assert await service.create_notification(session, "type", "subject", "message") is created
    assert service.send_expiry_warning_email("project", "mail@example.com", "2026-04-01", 2) is True
    assert await service.send_expiry_warning_telegram("chat", "project", "2026-04-01", 2) is True


class _FakeSession:
    def __init__(self, fail_on_flush=False):
        self.fail_on_flush = fail_on_flush
        self.added = []
        self.flush_calls = 0
        self.commit_calls = 0
        self.refresh_calls = []
        self.rollback_calls = 0

    def add(self, obj):
        obj.id = 1
        self.added.append(obj)

    async def flush(self):
        self.flush_calls += 1
        if self.fail_on_flush:
            raise RuntimeError("db flush failed")

    async def commit(self):
        self.commit_calls += 1

    async def refresh(self, obj):
        self.refresh_calls.append(obj)

    async def rollback(self):
        self.rollback_calls += 1


def _notification_service_module():
    return importlib.import_module("app.services.notification_service")
