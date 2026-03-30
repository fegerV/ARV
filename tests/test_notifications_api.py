from datetime import datetime, timezone
from types import SimpleNamespace

import httpx
import pytest
from fastapi import BackgroundTasks, HTTPException


@pytest.mark.asyncio
async def test_list_notifications_builds_paginated_payload():
    from app.api.routes import notifications

    created_at = datetime.now(timezone.utc).replace(tzinfo=None)
    item = SimpleNamespace(
        id=11,
        subject="System alert",
        message="Check storage",
        notification_type="system_alert",
        created_at=created_at,
        notification_metadata={
            "title": "Ignored title",
            "company_name": "Vertex",
            "project_name": "Demo",
            "ar_content_name": "Marker",
            "is_read": True,
            "read_at": created_at.isoformat(),
        },
    )
    db = _FakeDb(
        execute_results=[
            _FakeScalarsResult([item]),
            _FakeScalarResult(3),
        ]
    )

    result = await notifications.list_notifications(
        limit=2,
        offset=2,
        db=db,
        current_user=SimpleNamespace(),
    )

    assert result.total == 3
    assert result.page == 2
    assert result.page_size == 2
    assert result.total_pages == 2
    assert result.items[0].title == "System alert"
    assert result.items[0].company_name == "Vertex"
    assert result.items[0].is_read is True


@pytest.mark.asyncio
async def test_mark_all_notifications_read_updates_only_unread_rows():
    from app.api.routes import notifications

    db = _FakeDb(
        execute_results=[
            _FakeRowsResult(
                [
                    (1, {"is_read": False}),
                    (2, {"is_read": True, "read_at": "already"}),
                    (3, None),
                ]
            )
        ]
    )

    result = await notifications.mark_all_notifications_read(db=db, current_user=SimpleNamespace())

    assert result.success is True
    assert result.message == "Marked 2 notifications as read"
    assert len(db.update_calls) == 2
    assert db.commit_calls == 1
    first_meta = next(iter(db.update_calls[0].values()))
    second_meta = next(iter(db.update_calls[1].values()))
    assert first_meta["is_read"] is True
    assert second_meta["is_read"] is True


@pytest.mark.asyncio
async def test_mark_notifications_read_handles_empty_ids():
    from app.api.routes import notifications

    result = await notifications.mark_notifications_read([], db=_FakeDb(), current_user=SimpleNamespace())

    assert result.success is False
    assert result.message == "No notification IDs provided"


@pytest.mark.asyncio
async def test_mark_notifications_read_updates_unread_items():
    from app.api.routes import notifications

    items = [
        SimpleNamespace(id=1, notification_metadata={"is_read": False}),
        SimpleNamespace(id=2, notification_metadata={"is_read": True}),
        SimpleNamespace(id=3, notification_metadata=None),
    ]
    db = _FakeDb(execute_results=[_FakeScalarsResult(items)])

    result = await notifications.mark_notifications_read([1, 2, 3], db=db, current_user=SimpleNamespace())

    assert result.success is True
    assert result.message == "Marked 2 notifications as read"
    assert items[0].notification_metadata["is_read"] is True
    assert items[2].notification_metadata["is_read"] is True
    assert db.commit_calls == 1


@pytest.mark.asyncio
async def test_delete_notification_raises_for_missing_item():
    from app.api.routes import notifications

    with pytest.raises(HTTPException) as exc_info:
        await notifications.delete_notification(404, db=_FakeDb(), current_user=SimpleNamespace())

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Notification not found"


@pytest.mark.asyncio
async def test_create_notification_endpoint_serializes_service_response(monkeypatch):
    from app.api.routes import notifications

    created_at = datetime.now(timezone.utc).replace(tzinfo=None)

    async def _fake_create_notification(**_kwargs):
        return SimpleNamespace(
            id=15,
            subject="AR Ready",
            message="Viewer updated",
            notification_type="ar_ready",
            created_at=created_at,
            notification_metadata={"company_name": "Vertex", "is_read": False},
        )

    monkeypatch.setattr(notifications, "create_notification", _fake_create_notification)

    result = await notifications.create_notification_endpoint(
        notifications.NotificationCreate(
            notification_type="ar_ready",
            subject="AR Ready",
            message="Viewer updated",
            company_id=7,
        ),
        db=_FakeDb(),
        current_user=SimpleNamespace(),
    )

    assert result.id == 15
    assert result.title == "AR Ready"
    assert result.type == "ar_ready"
    assert result.company_name == "Vertex"
    assert result.is_read is False


@pytest.mark.asyncio
async def test_test_notification_queues_email_and_optional_telegram(monkeypatch):
    from app.api.routes import notifications

    cfg = SimpleNamespace(TELEGRAM_BOT_TOKEN="bot-token")
    monkeypatch.setattr(notifications, "settings", cfg)

    tasks = BackgroundTasks()
    result = await notifications.test_notification("ops@example.com", "12345", tasks)

    assert result == {"status": "queued"}
    assert len(tasks.tasks) == 2


@pytest.mark.asyncio
async def test_test_telegram_from_settings_requires_tokens(monkeypatch):
    from app.api.routes import notifications

    class FakeSettingsService:
        def __init__(self, _db):
            pass

        async def get_all_settings(self):
            return SimpleNamespace(
                notifications=SimpleNamespace(
                    telegram_bot_token="",
                    telegram_admin_chat_id="",
                )
            )

    monkeypatch.setitem(__import__("sys").modules, "app.services.settings_service", SimpleNamespace(SettingsService=FakeSettingsService))

    result = await notifications.test_telegram_from_settings(
        db=_FakeDb(),
        current_user=SimpleNamespace(),
        telegram_bot_token="",
        telegram_admin_chat_id="",
    )

    assert result["status"] == "error"
    assert "Bot Token" in result["detail"]


@pytest.mark.asyncio
async def test_test_telegram_from_settings_reports_telegram_error(monkeypatch):
    from app.api.routes import notifications

    class FakeSettingsService:
        def __init__(self, _db):
            pass

        async def get_all_settings(self):
            return SimpleNamespace(
                notifications=SimpleNamespace(
                    telegram_bot_token="bot-token",
                    telegram_admin_chat_id="12345",
                )
            )

    class FakeResponse:
        status_code = 400

        @staticmethod
        def json():
            return {"description": "chat not found"}

    class FakeAsyncClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json):
            assert "bot-token" in url
            assert json["chat_id"] == "12345"
            return FakeResponse()

    monkeypatch.setitem(__import__("sys").modules, "app.services.settings_service", SimpleNamespace(SettingsService=FakeSettingsService))
    monkeypatch.setattr(notifications.httpx, "AsyncClient", FakeAsyncClient)

    result = await notifications.test_telegram_from_settings(
        db=_FakeDb(),
        current_user=SimpleNamespace(),
        telegram_bot_token="",
        telegram_admin_chat_id="",
    )

    assert result == {"status": "error", "detail": "chat not found"}


@pytest.mark.asyncio
async def test_test_telegram_from_settings_prefers_current_form_values(monkeypatch):
    from app.api.routes import notifications

    class FakeSettingsService:
        def __init__(self, _db):
            pass

        async def get_all_settings(self):
            return SimpleNamespace(
                notifications=SimpleNamespace(
                    telegram_bot_token="db-token",
                    telegram_admin_chat_id="db-chat",
                )
            )

    class FakeResponse:
        status_code = 200

    captured = {}

    class FakeAsyncClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json):
            captured["url"] = url
            captured["chat_id"] = json["chat_id"]
            return FakeResponse()

    monkeypatch.setitem(__import__("sys").modules, "app.services.settings_service", SimpleNamespace(SettingsService=FakeSettingsService))
    monkeypatch.setattr(notifications.httpx, "AsyncClient", FakeAsyncClient)

    result = await notifications.test_telegram_from_settings(
        db=_FakeDb(),
        current_user=SimpleNamespace(),
        telegram_bot_token="form-token",
        telegram_admin_chat_id="form-chat",
    )

    assert result["status"] == "ok"
    assert "form-token" in captured["url"]
    assert captured["chat_id"] == "form-chat"


@pytest.mark.asyncio
async def test_test_email_from_settings_uses_form_values(monkeypatch):
    from app.api.routes import notifications

    class FakeSettingsService:
        def __init__(self, _db):
            pass

        async def get_all_settings(self):
            return SimpleNamespace(
                notifications=SimpleNamespace(
                    smtp_host="db.smtp.example.com",
                    smtp_port=25,
                    smtp_username="db-user",
                    smtp_password="db-pass",
                    smtp_from_email="db@example.com",
                )
            )

    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            sent["host"] = host
            sent["port"] = port
            sent["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def starttls(self):
            sent["starttls"] = True

        def login(self, username, password):
            sent["login"] = (username, password)

        def send_message(self, msg):
            sent["from"] = msg["From"]
            sent["to"] = msg["To"]

    monkeypatch.setitem(__import__("sys").modules, "app.services.settings_service", SimpleNamespace(SettingsService=FakeSettingsService))
    monkeypatch.setattr(notifications.smtplib, "SMTP", FakeSMTP)

    result = await notifications.test_email_from_settings(
        smtp_host="smtp.example.com",
        smtp_port=2525,
        smtp_username="mailer",
        smtp_password="secret",
        smtp_from_email="noreply@example.com",
        db=_FakeDb(),
        current_user=SimpleNamespace(email="admin@example.com"),
    )

    assert result["status"] == "ok"
    assert sent["host"] == "smtp.example.com"
    assert sent["port"] == 2525
    assert sent["login"] == ("mailer", "secret")
    assert sent["from"] == "noreply@example.com"
    assert sent["to"] == "admin@example.com"


class _FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar(self):
        return self._value


class _FakeScalars:
    def __init__(self, values):
        self._values = list(values)

    def all(self):
        return list(self._values)


class _FakeScalarsResult:
    def __init__(self, values):
        self._values = list(values)

    def scalars(self):
        return _FakeScalars(self._values)


class _FakeRowsResult:
    def __init__(self, rows):
        self._rows = list(rows)

    def all(self):
        return list(self._rows)


class _FakeDb:
    def __init__(self, get_map=None, execute_results=None):
        self.get_map = get_map or {}
        self.execute_results = list(execute_results or [])
        self.update_calls = []
        self.deleted = None
        self.commit_calls = 0

    async def get(self, model, pk):
        return self.get_map.get((model, pk))

    async def execute(self, stmt):
        if hasattr(stmt, "table") and hasattr(stmt, "_values"):
            normalized = {}
            for key, value in stmt._values.items():
                normalized[str(key)] = getattr(value, "value", value)
            self.update_calls.append(normalized)
            return None
        return self.execute_results.pop(0)

    async def delete(self, obj):
        self.deleted = obj

    async def commit(self):
        self.commit_calls += 1
