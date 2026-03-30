from types import MethodType, SimpleNamespace

import pytest

from app.models.settings import SystemSettings
from app.schemas.settings import (
    APISettings,
    ARSettings,
    BackupSettings,
    GeneralSettings,
    IntegrationSettings,
    NotificationSettings,
    SecuritySettings,
    StorageSettings,
)
from app.services.settings_service import SettingsService


def test_parse_setting_value_handles_supported_types():
    valid_json = SystemSettings(key="cors", value='["https://example.com"]', data_type="json")
    invalid_json = SystemSettings(key="cors", value="{oops", data_type="json")
    true_bool = SystemSettings(key="enabled", value="TRUE", data_type="boolean")
    integer_value = SystemSettings(key="timeout", value="42", data_type="integer")
    invalid_integer = SystemSettings(key="timeout", value="forty-two", data_type="integer")
    string_value = SystemSettings(key="title", value="Vertex", data_type="string")

    assert SettingsService._parse_setting_value(None) is None
    assert SettingsService._parse_setting_value(valid_json) == ["https://example.com"]
    assert SettingsService._parse_setting_value(invalid_json) == "{oops"
    assert SettingsService._parse_setting_value(true_bool) is True
    assert SettingsService._parse_setting_value(integer_value) == 42
    assert SettingsService._parse_setting_value(invalid_integer) == "forty-two"
    assert SettingsService._parse_setting_value(string_value) == "Vertex"


@pytest.mark.asyncio
async def test_get_setting_and_category_queries_return_scalars():
    site_title = SystemSettings(key="site_title", value="Vertex", category="general")
    timezone = SystemSettings(key="timezone", value="UTC", category="general")
    session = _FakeSession(
        execute_results=[
            _FakeExecuteResult(one=site_title),
            _FakeExecuteResult(many=[site_title, timezone]),
        ]
    )
    service = SettingsService(session)

    assert await service.get_setting("site_title") is site_title
    assert await service.get_settings_by_category("general") == [site_title, timezone]


@pytest.mark.asyncio
async def test_get_setting_value_and_get_int_setting_use_safe_defaults():
    session = _FakeSession()
    service = SettingsService(session)

    async def _fake_get_setting(self, key):
        mapping = {
            "missing": None,
            "number": SystemSettings(key="number", value="25", data_type="integer"),
            "broken": SystemSettings(key="broken", value="oops", data_type="integer"),
        }
        return mapping[key]

    service.get_setting = MethodType(_fake_get_setting, service)

    assert await service.get_setting_value("missing", "fallback") == "fallback"
    assert await service.get_setting_value("number", 0) == 25
    assert await service.get_int_setting("number", 9) == 25
    assert await service.get_int_setting("broken", 9) == 9


@pytest.mark.asyncio
async def test_set_setting_creates_and_updates_records():
    created_session = _FakeSession(execute_results=[_FakeExecuteResult(one=None)])
    created_service = SettingsService(created_session)

    created = await created_service.set_setting(
        "cors_origins",
        ["https://example.com"],
        data_type="json",
        category="api",
        description="Allowed origins",
        is_public=True,
    )

    assert created_session.added == [created]
    assert created.value == '["https://example.com"]'
    assert created.data_type == "json"
    assert created.category == "api"
    assert created.description == "Allowed origins"
    assert created.is_public is True
    assert created_session.commit_calls == 1
    assert created_session.refresh_calls == [created]
    assert created_session.flush_calls == 0

    existing = SystemSettings(
        key="maintenance_mode",
        value="false",
        data_type="boolean",
        category="general",
        description="Old",
        is_public=False,
    )
    update_session = _FakeSession(execute_results=[_FakeExecuteResult(one=existing)])
    update_service = SettingsService(update_session)

    updated = await update_service.set_setting(
        "maintenance_mode",
        True,
        data_type="boolean",
        category="general",
        description="New",
        is_public=True,
        commit=False,
    )

    assert updated is existing
    assert existing.value == "true"
    assert existing.description == "New"
    assert existing.is_public is True
    assert update_session.commit_calls == 0
    assert update_session.refresh_calls == []
    assert update_session.flush_calls == 1


@pytest.mark.asyncio
async def test_set_setting_creates_record_without_commit_when_requested():
    session = _FakeSession(execute_results=[_FakeExecuteResult(one=None)])
    service = SettingsService(session)

    created = await service.set_setting(
        "backup_cron",
        "0 3 * * *",
        data_type="string",
        category="backup",
        commit=False,
    )

    assert session.added == [created]
    assert created.key == "backup_cron"
    assert created.value == "0 3 * * *"
    assert created.category == "backup"
    assert session.commit_calls == 0
    assert session.refresh_calls == []
    assert session.flush_calls == 1


@pytest.mark.asyncio
async def test_get_all_settings_combines_defaults_and_db_values():
    rows = [
        SystemSettings(key="site_title", value="Custom title", data_type="string"),
        SystemSettings(key="maintenance_mode", value="true", data_type="boolean"),
        SystemSettings(key="default_subscription_years", value="3", data_type="integer"),
        SystemSettings(key="telegram_2fa_chat_id", value="", data_type="string"),
        SystemSettings(key="cors_origins", value='["https://app.example.com"]', data_type="json"),
        SystemSettings(key="payment_provider", value="paypal", data_type="string"),
        SystemSettings(key="analytics_enabled", value="true", data_type="boolean"),
        SystemSettings(key="backup_company_id", value="12", data_type="integer"),
        SystemSettings(key="backup_enabled", value="true", data_type="boolean"),
        SystemSettings(key="backup_max_copies", value="7", data_type="integer"),
    ]
    session = _FakeSession(execute_results=[_FakeExecuteResult(many=rows)])

    result = await SettingsService(session).get_all_settings()

    assert result.general.site_title == "Custom title"
    assert result.general.maintenance_mode is True
    assert result.general.default_subscription_years == 3
    assert result.security.telegram_2fa_chat_id is None
    assert result.security.session_timeout == 60
    assert result.storage.default_storage == "local"
    assert result.notifications.smtp_password is None
    assert result.notifications.telegram_alerts_enabled is False
    assert result.api.cors_origins == ["https://app.example.com"]
    assert result.integrations.payment_provider == "paypal"
    assert result.integrations.analytics_enabled is True
    assert result.backup.backup_enabled is True
    assert result.backup.backup_company_id == 12
    assert result.backup.backup_max_copies == 7
    assert result.backup.backup_yd_folder == "backups"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "settings_obj", "expected_calls"),
    [
        (
            "update_general_settings",
            GeneralSettings(
                site_title="Vertex",
                admin_email="ops@example.com",
                site_description="desc",
                maintenance_mode=True,
                timezone="Asia/Yekaterinburg",
                language="ru",
                default_subscription_years=2,
            ),
            [
                ("site_title", "Vertex", "string", "general"),
                ("admin_email", "ops@example.com", "string", "general"),
                ("site_description", "desc", "string", "general"),
                ("maintenance_mode", True, "boolean", "general"),
                ("timezone", "Asia/Yekaterinburg", "string", "general"),
                ("language", "ru", "string", "general"),
                ("default_subscription_years", 2, "integer", "general"),
            ],
        ),
        (
            "update_security_settings",
            SecuritySettings(
                password_min_length=10,
                session_timeout=120,
                require_2fa=True,
                telegram_2fa_chat_id=None,
                max_login_attempts=4,
                lockout_duration=600,
                api_rate_limit=99,
            ),
            [
                ("password_min_length", 10, "integer", "security"),
                ("session_timeout", 120, "integer", "security"),
                ("require_2fa", True, "boolean", "security"),
                ("telegram_2fa_chat_id", None, "string", "security"),
                ("max_login_attempts", 4, "integer", "security"),
                ("lockout_duration", 600, "integer", "security"),
                ("api_rate_limit", 99, "integer", "security"),
            ],
        ),
        (
            "update_storage_settings",
            StorageSettings(
                default_storage="yandex",
                max_file_size=256,
                cdn_enabled=True,
                cdn_url="https://cdn.example.com",
                backup_enabled=False,
                backup_retention_days=14,
            ),
            [
                ("default_storage", "yandex", "string", "storage"),
                ("max_file_size", 256, "integer", "storage"),
                ("cdn_enabled", True, "boolean", "storage"),
                ("cdn_url", "https://cdn.example.com", "string", "storage"),
                ("backup_enabled", False, "boolean", "storage"),
                ("backup_retention_days", 14, "integer", "storage"),
            ],
        ),
        (
            "update_notification_settings",
            NotificationSettings(
                email_enabled=False,
                smtp_host="smtp.example.com",
                smtp_port=2525,
                smtp_username="mailer",
                smtp_password="secret",
                smtp_from_email="noreply@example.com",
                telegram_enabled=True,
                telegram_bot_token="token",
                telegram_admin_chat_id="123",
                telegram_alerts_enabled=True,
                alert_on_critical=True,
                alert_on_warning=True,
                alert_on_backup_failed=False,
                alert_on_storage_failed=False,
                alert_on_health_degraded=True,
            ),
            [
                ("email_enabled", False, "boolean", "notifications"),
                ("smtp_host", "smtp.example.com", "string", "notifications"),
                ("smtp_port", 2525, "integer", "notifications"),
                ("smtp_username", "mailer", "string", "notifications"),
                ("smtp_password", "secret", "string", "notifications"),
                ("smtp_from_email", "noreply@example.com", "string", "notifications"),
                ("telegram_enabled", True, "boolean", "notifications"),
                ("telegram_bot_token", "token", "string", "notifications"),
                ("telegram_admin_chat_id", "123", "string", "notifications"),
                ("telegram_alerts_enabled", True, "boolean", "notifications"),
                ("alert_on_critical", True, "boolean", "notifications"),
                ("alert_on_warning", True, "boolean", "notifications"),
                ("alert_on_backup_failed", False, "boolean", "notifications"),
                ("alert_on_storage_failed", False, "boolean", "notifications"),
                ("alert_on_health_degraded", True, "boolean", "notifications"),
            ],
        ),
        (
            "update_api_settings",
            APISettings(
                api_keys_enabled=False,
                webhook_enabled=True,
                webhook_url="https://hooks.example.com",
                documentation_public=False,
                cors_origins=["https://app.example.com"],
            ),
            [
                ("api_keys_enabled", False, "boolean", "api"),
                ("webhook_enabled", True, "boolean", "api"),
                ("webhook_url", "https://hooks.example.com", "string", "api"),
                ("documentation_public", False, "boolean", "api"),
                ("cors_origins", ["https://app.example.com"], "json", "api"),
            ],
        ),
        (
            "update_integration_settings",
            IntegrationSettings(
                google_oauth_enabled=True,
                google_client_id="client-id",
                payment_provider="paypal",
                stripe_public_key="pk_test",
                analytics_enabled=True,
                analytics_provider="plausible",
            ),
            [
                ("google_oauth_enabled", True, "boolean", "integrations"),
                ("google_client_id", "client-id", "string", "integrations"),
                ("payment_provider", "paypal", "string", "integrations"),
                ("stripe_public_key", "pk_test", "string", "integrations"),
                ("analytics_enabled", True, "boolean", "integrations"),
                ("analytics_provider", "plausible", "string", "integrations"),
            ],
        ),
        (
            "update_ar_settings",
            ARSettings(
                mindar_max_features=1500,
                marker_generation_enabled=False,
                thumbnail_quality=90,
                video_processing_enabled=False,
                default_ar_viewer_theme="light",
                qr_code_expiration_days=90,
            ),
            [
                ("mindar_max_features", 1500, "integer", "ar"),
                ("marker_generation_enabled", False, "boolean", "ar"),
                ("thumbnail_quality", 90, "integer", "ar"),
                ("video_processing_enabled", False, "boolean", "ar"),
                ("default_ar_viewer_theme", "light", "string", "ar"),
                ("qr_code_expiration_days", 90, "integer", "ar"),
            ],
        ),
        (
            "update_backup_settings",
            BackupSettings(
                backup_enabled=True,
                backup_company_id=33,
                backup_yd_folder="nightly",
                backup_schedule="weekly",
                backup_cron="0 2 * * 0",
                backup_retention_days=21,
                backup_max_copies=9,
            ),
            [
                ("backup_enabled", True, "boolean", "backup"),
                ("backup_company_id", 33, "integer", "backup"),
                ("backup_yd_folder", "nightly", "string", "backup"),
                ("backup_schedule", "weekly", "string", "backup"),
                ("backup_cron", "0 2 * * 0", "string", "backup"),
                ("backup_retention_days", 21, "integer", "backup"),
                ("backup_max_copies", 9, "integer", "backup"),
            ],
        ),
    ],
)
async def test_update_methods_queue_expected_setting_writes(method_name, settings_obj, expected_calls):
    session = _FakeSession()
    service = SettingsService(session)
    captured_calls = []

    async def _fake_set_setting(self, key, value, data_type="string", category="general", description=None, is_public=False, commit=True):
        captured_calls.append((key, value, data_type, category, commit))
        return SimpleNamespace(key=key, value=value)

    service.set_setting = MethodType(_fake_set_setting, service)

    result = await getattr(service, method_name)(settings_obj)

    assert result == settings_obj
    assert captured_calls == [(*call, False) for call in expected_calls]
    assert session.commit_calls == 1


class _FakeScalars:
    def __init__(self, values):
        self._values = list(values)

    def all(self):
        return list(self._values)


class _FakeExecuteResult:
    def __init__(self, many=None, one=None):
        self._many = list(many or [])
        self._one = one

    def scalars(self):
        return _FakeScalars(self._many)

    def scalar_one_or_none(self):
        return self._one


class _FakeSession:
    def __init__(self, execute_results=None):
        self.execute_results = list(execute_results or [])
        self.added = []
        self.commit_calls = 0
        self.refresh_calls = []
        self.flush_calls = 0

    async def execute(self, _stmt):
        return self.execute_results.pop(0)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commit_calls += 1

    async def refresh(self, obj):
        self.refresh_calls.append(obj)

    async def flush(self):
        self.flush_calls += 1
