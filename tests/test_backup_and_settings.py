"""Tests for backup system, settings schemas, and common fixes."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


def test_backup_settings_defaults():
    """BackupSettings has correct default values."""
    from app.schemas.settings import BackupSettings

    s = BackupSettings()
    assert s.backup_enabled is False
    assert s.backup_company_id is None
    assert s.backup_yd_folder == "backups"
    assert s.backup_schedule == "daily"
    assert s.backup_cron == "0 3 * * *"
    assert s.backup_retention_days == 30
    assert s.backup_max_copies == 30


def test_backup_settings_custom_values():
    """BackupSettings accepts custom values."""
    from app.schemas.settings import BackupSettings

    s = BackupSettings(
        backup_enabled=True,
        backup_company_id=5,
        backup_yd_folder="my_backups",
        backup_schedule="weekly",
        backup_cron="0 3 * * 1",
        backup_retention_days=7,
        backup_max_copies=10,
    )
    assert s.backup_enabled is True
    assert s.backup_company_id == 5
    assert s.backup_yd_folder == "my_backups"
    assert s.backup_max_copies == 10


def test_setting_category_has_backup():
    """SettingCategory enum includes BACKUP."""
    from app.schemas.settings import SettingCategory

    assert hasattr(SettingCategory, "BACKUP")
    assert SettingCategory.BACKUP.value == "backup"


def test_all_settings_includes_backup():
    """AllSettings model includes the backup field."""
    from app.schemas.settings import AllSettings

    fields = AllSettings.model_fields
    assert "backup" in fields


# ---------------------------------------------------------------------------
# Backup model tests
# ---------------------------------------------------------------------------


def test_backup_history_model_fields():
    """BackupHistory model has the expected columns."""
    from app.models.backup import BackupHistory

    assert hasattr(BackupHistory, "id")
    assert hasattr(BackupHistory, "started_at")
    assert hasattr(BackupHistory, "finished_at")
    assert hasattr(BackupHistory, "status")
    assert hasattr(BackupHistory, "size_bytes")
    assert hasattr(BackupHistory, "yd_path")
    assert hasattr(BackupHistory, "company_id")
    assert hasattr(BackupHistory, "error_message")
    assert hasattr(BackupHistory, "trigger")
    assert BackupHistory.__tablename__ == "backup_history"


# ---------------------------------------------------------------------------
# BackupService unit tests
# ---------------------------------------------------------------------------


def test_parse_database_url_postgres():
    """_parse_database_url correctly extracts PG connection params."""
    from app.services.backup_service import _parse_database_url

    url = "postgresql+asyncpg://myuser:mypass@db.host:5433/mydb"
    result = _parse_database_url(url)
    assert result["host"] == "db.host"
    assert result["port"] == "5433"
    assert result["dbname"] == "mydb"
    assert result["user"] == "myuser"
    assert result["password"] == "mypass"


def test_parse_database_url_defaults():
    """_parse_database_url returns defaults for minimal URL."""
    from app.services.backup_service import _parse_database_url

    url = "postgresql://localhost/testdb"
    result = _parse_database_url(url)
    assert result["host"] == "localhost"
    assert result["port"] == "5432"
    assert result["dbname"] == "testdb"
    assert result["user"] is not None


def test_parse_database_url_sqlite():
    """_parse_database_url handles sqlite URLs gracefully."""
    from app.services.backup_service import _parse_database_url

    url = "sqlite+aiosqlite:///./test.db"
    result = _parse_database_url(url)
    assert isinstance(result, dict)
    assert "host" in result


# ---------------------------------------------------------------------------
# Scheduler tests
# ---------------------------------------------------------------------------


def test_scheduler_module_importable():
    """The scheduler module can be imported without errors."""
    from app.core.scheduler import scheduler, reschedule_backup

    assert scheduler is not None
    assert callable(reschedule_backup)


# ---------------------------------------------------------------------------
# API endpoints smoke tests (no DB required)
# ---------------------------------------------------------------------------


def test_app_has_backup_routes():
    """Backup routes are registered on the application."""
    from app.main import app

    routes = [r.path for r in app.routes]
    assert "/api/backups/run" in routes or any("/backups/run" in r for r in routes)


@pytest.mark.asyncio
async def test_backup_endpoints_require_auth():
    """Backup API endpoints return 401/403 when not authenticated."""
    import httpx
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp_run = await client.post("/api/backups/run")
        assert resp_run.status_code in (401, 403, 307, 303)

        resp_history = await client.get("/api/backups/history")
        assert resp_history.status_code in (401, 403, 307, 303)

        resp_status = await client.get("/api/backups/status")
        assert resp_status.status_code in (401, 403, 307, 303)


# ---------------------------------------------------------------------------
# Settings page smoke test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_settings_page_returns_200_or_redirect():
    """GET /settings returns 200 (authenticated) or 303 (redirect to login)."""
    import httpx
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver", follow_redirects=False) as client:
        resp = await client.get("/settings")
        assert resp.status_code in (200, 303)


# ---------------------------------------------------------------------------
# Health check (general sanity)
# ---------------------------------------------------------------------------


def test_no_debug_endpoint_in_production():
    """The debug/storage-test endpoint should NOT be registered."""
    from app.main import app

    routes = [r.path for r in app.routes]
    assert "/debug/storage-test" not in routes
