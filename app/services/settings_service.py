from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Any, Optional, List
from app.models.settings import SystemSettings
from app.schemas.settings import (
    AllSettings, GeneralSettings, SecuritySettings, StorageSettings,
    NotificationSettings, APISettings, IntegrationSettings, ARSettings,
    BackupSettings,
)
import json
import logging

logger = logging.getLogger(__name__)

class SettingsService:
    """Service for managing system settings."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_setting(self, key: str) -> Optional[SystemSettings]:
        """Get a single setting by key."""
        result = await self.db.execute(
            select(SystemSettings).where(SystemSettings.key == key)
        )
        return result.scalar_one_or_none()
    
    async def get_settings_by_category(self, category: str) -> List[SystemSettings]:
        """Get all settings in a category."""
        result = await self.db.execute(
            select(SystemSettings).where(SystemSettings.category == category)
        )
        return result.scalars().all()

    @staticmethod
    def _parse_setting_value(setting: Optional[SystemSettings]) -> Any:
        """Convert DB string value to its declared Python type."""
        if setting is None or setting.value is None:
            return None
        if setting.data_type == "json":
            try:
                return json.loads(setting.value)
            except json.JSONDecodeError:
                return setting.value
        if setting.data_type == "boolean":
            return setting.value.lower() == "true"
        if setting.data_type == "integer":
            try:
                return int(setting.value)
            except ValueError:
                return setting.value
        return setting.value

    async def get_setting_value(self, key: str, default: Any = None) -> Any:
        """Return one setting already converted to its Python type."""
        setting = await self.get_setting(key)
        value = self._parse_setting_value(setting)
        return default if value is None else value

    async def get_int_setting(self, key: str, default: int) -> int:
        """Return one integer setting with a safe fallback."""
        value = await self.get_setting_value(key, default)
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
    
    async def set_setting(
        self, 
        key: str, 
        value: Any, 
        data_type: str = "string",
        category: str = "general",
        description: Optional[str] = None,
        is_public: bool = False,
        commit: bool = True,
    ) -> SystemSettings:
        """Set a setting value."""
        # Convert value to string based on data type
        if data_type == "json":
            str_value = json.dumps(value) if value is not None else None
        elif data_type == "boolean":
            str_value = str(value).lower() if isinstance(value, bool) else str(value)
        elif data_type == "integer":
            str_value = str(int(value)) if value is not None else None
        else:
            str_value = str(value) if value is not None else None
        
        # Check if setting exists
        setting = await self.get_setting(key)
        if setting:
            setting.value = str_value
            setting.data_type = data_type
            setting.description = description
            setting.is_public = is_public
        else:
            setting = SystemSettings(
                key=key,
                value=str_value,
                data_type=data_type,
                category=category,
                description=description,
                is_public=is_public
            )
            self.db.add(setting)
        
        if commit:
            await self.db.commit()
            await self.db.refresh(setting)
        else:
            await self.db.flush()
        return setting
    
    async def get_all_settings(self) -> AllSettings:
        """Get all settings grouped by category."""
        # Get all settings from database
        result = await self.db.execute(select(SystemSettings))
        all_db_settings = result.scalars().all()
        
        # Convert to dict for easy access
        settings_dict = {}
        for setting in all_db_settings:
            settings_dict[setting.key] = self._parse_setting_value(setting)
        
        # Build settings objects
        general = GeneralSettings(
            site_title=settings_dict.get("site_title", "Vertex AR B2B Platform"),
            admin_email=settings_dict.get("admin_email", "admin@vertexar.com"),
            site_description=settings_dict.get("site_description", "B2B SaaS platform for creating AR content based on image recognition (NFT markers)"),
            maintenance_mode=settings_dict.get("maintenance_mode", False),
            timezone=settings_dict.get("timezone", "UTC"),
            language=settings_dict.get("language", "en"),
            default_subscription_years=settings_dict.get("default_subscription_years", 1)
        )
        
        security = SecuritySettings(
            password_min_length=settings_dict.get("password_min_length", 8),
            session_timeout=settings_dict.get("session_timeout", 60),
            require_2fa=settings_dict.get("require_2fa", False),
            telegram_2fa_chat_id=settings_dict.get("telegram_2fa_chat_id") or None,
            max_login_attempts=settings_dict.get("max_login_attempts", 5),
            lockout_duration=settings_dict.get("lockout_duration", 300),
            api_rate_limit=settings_dict.get("api_rate_limit", 100)
        )
        
        storage = StorageSettings(
            default_storage=settings_dict.get("default_storage", "local"),
            max_file_size=settings_dict.get("max_file_size", 100),
            cdn_enabled=settings_dict.get("cdn_enabled", False),
            cdn_url=settings_dict.get("cdn_url"),
            backup_enabled=settings_dict.get("backup_enabled", True),
            backup_retention_days=settings_dict.get("backup_retention_days", 30)
        )
        
        notifications = NotificationSettings(
            email_enabled=settings_dict.get("email_enabled", True),
            smtp_host=settings_dict.get("smtp_host"),
            smtp_port=settings_dict.get("smtp_port", 587),
            smtp_username=settings_dict.get("smtp_username"),
            smtp_password=settings_dict.get("smtp_password"),
            smtp_from_email=settings_dict.get("smtp_from_email", "noreply@vertexar.com"),
            telegram_enabled=settings_dict.get("telegram_enabled", False),
            telegram_bot_token=settings_dict.get("telegram_bot_token"),
            telegram_admin_chat_id=settings_dict.get("telegram_admin_chat_id"),
            telegram_alerts_enabled=settings_dict.get("telegram_alerts_enabled", False),
            alert_on_critical=settings_dict.get("alert_on_critical", True),
            alert_on_warning=settings_dict.get("alert_on_warning", False),
            alert_on_backup_failed=settings_dict.get("alert_on_backup_failed", True),
            alert_on_storage_failed=settings_dict.get("alert_on_storage_failed", True),
            alert_on_health_degraded=settings_dict.get("alert_on_health_degraded", True),
        )
        
        api = APISettings(
            api_keys_enabled=settings_dict.get("api_keys_enabled", True),
            webhook_enabled=settings_dict.get("webhook_enabled", False),
            webhook_url=settings_dict.get("webhook_url"),
            documentation_public=settings_dict.get("documentation_public", True),
            cors_origins=settings_dict.get("cors_origins", ["http://localhost:3000", "http://localhost:8000"])
        )
        
        integrations = IntegrationSettings(
            google_oauth_enabled=settings_dict.get("google_oauth_enabled", False),
            google_client_id=settings_dict.get("google_client_id"),
            payment_provider=settings_dict.get("payment_provider", "stripe"),
            stripe_public_key=settings_dict.get("stripe_public_key"),
            analytics_enabled=settings_dict.get("analytics_enabled", False),
            analytics_provider=settings_dict.get("analytics_provider", "google")
        )
        
        ar = ARSettings(
            mindar_max_features=settings_dict.get("mindar_max_features", 1000),
            marker_generation_enabled=settings_dict.get("marker_generation_enabled", True),
            thumbnail_quality=settings_dict.get("thumbnail_quality", 80),
            video_processing_enabled=settings_dict.get("video_processing_enabled", True),
            default_ar_viewer_theme=settings_dict.get("default_ar_viewer_theme", "default"),
            qr_code_expiration_days=settings_dict.get("qr_code_expiration_days", 365)
        )
        
        backup = BackupSettings(
            backup_enabled=settings_dict.get("backup_enabled", False),
            backup_company_id=settings_dict.get("backup_company_id"),
            backup_yd_folder=settings_dict.get("backup_yd_folder", "backups"),
            backup_schedule=settings_dict.get("backup_schedule", "daily"),
            backup_cron=settings_dict.get("backup_cron", "0 3 * * *"),
            backup_retention_days=settings_dict.get("backup_retention_days", 30),
            backup_max_copies=settings_dict.get("backup_max_copies", 30),
        )

        return AllSettings(
            general=general,
            security=security,
            storage=storage,
            notifications=notifications,
            api=api,
            integrations=integrations,
            ar=ar,
            backup=backup,
        )
    
    async def update_general_settings(self, settings: GeneralSettings) -> GeneralSettings:
        """Update general settings."""
        await self.set_setting("site_title", settings.site_title, "string", "general", commit=False)
        await self.set_setting("admin_email", settings.admin_email, "string", "general", commit=False)
        await self.set_setting("site_description", settings.site_description, "string", "general", commit=False)
        await self.set_setting("maintenance_mode", settings.maintenance_mode, "boolean", "general", commit=False)
        await self.set_setting("timezone", settings.timezone, "string", "general", commit=False)
        await self.set_setting("language", settings.language, "string", "general", commit=False)
        await self.set_setting("default_subscription_years", settings.default_subscription_years, "integer", "general", commit=False)
        
        await self.db.commit()
        return settings
    
    async def update_security_settings(self, settings: SecuritySettings) -> SecuritySettings:
        """Update security settings."""
        await self.set_setting("password_min_length", settings.password_min_length, "integer", "security", commit=False)
        await self.set_setting("session_timeout", settings.session_timeout, "integer", "security", commit=False)
        await self.set_setting("require_2fa", settings.require_2fa, "boolean", "security", commit=False)
        await self.set_setting("telegram_2fa_chat_id", settings.telegram_2fa_chat_id, "string", "security", commit=False)
        await self.set_setting("max_login_attempts", settings.max_login_attempts, "integer", "security", commit=False)
        await self.set_setting("lockout_duration", settings.lockout_duration, "integer", "security", commit=False)
        await self.set_setting("api_rate_limit", settings.api_rate_limit, "integer", "security", commit=False)
        
        await self.db.commit()
        return settings
    
    async def update_storage_settings(self, settings: StorageSettings) -> StorageSettings:
        """Update storage settings."""
        await self.set_setting("default_storage", settings.default_storage, "string", "storage", commit=False)
        await self.set_setting("max_file_size", settings.max_file_size, "integer", "storage", commit=False)
        await self.set_setting("cdn_enabled", settings.cdn_enabled, "boolean", "storage", commit=False)
        await self.set_setting("cdn_url", settings.cdn_url, "string", "storage", commit=False)
        await self.set_setting("backup_enabled", settings.backup_enabled, "boolean", "storage", commit=False)
        await self.set_setting("backup_retention_days", settings.backup_retention_days, "integer", "storage", commit=False)
        
        await self.db.commit()
        return settings
    
    async def update_notification_settings(self, settings: NotificationSettings) -> NotificationSettings:
        """Update notification settings."""
        await self.set_setting("email_enabled", settings.email_enabled, "boolean", "notifications", commit=False)
        await self.set_setting("smtp_host", settings.smtp_host, "string", "notifications", commit=False)
        await self.set_setting("smtp_port", settings.smtp_port, "integer", "notifications", commit=False)
        await self.set_setting("smtp_username", settings.smtp_username, "string", "notifications", commit=False)
        await self.set_setting("smtp_password", settings.smtp_password, "string", "notifications", commit=False)
        await self.set_setting("smtp_from_email", settings.smtp_from_email, "string", "notifications", commit=False)
        await self.set_setting("telegram_enabled", settings.telegram_enabled, "boolean", "notifications", commit=False)
        await self.set_setting("telegram_bot_token", settings.telegram_bot_token, "string", "notifications", commit=False)
        await self.set_setting("telegram_admin_chat_id", settings.telegram_admin_chat_id, "string", "notifications", commit=False)
        await self.set_setting("telegram_alerts_enabled", settings.telegram_alerts_enabled, "boolean", "notifications", commit=False)
        await self.set_setting("alert_on_critical", settings.alert_on_critical, "boolean", "notifications", commit=False)
        await self.set_setting("alert_on_warning", settings.alert_on_warning, "boolean", "notifications", commit=False)
        await self.set_setting("alert_on_backup_failed", settings.alert_on_backup_failed, "boolean", "notifications", commit=False)
        await self.set_setting("alert_on_storage_failed", settings.alert_on_storage_failed, "boolean", "notifications", commit=False)
        await self.set_setting("alert_on_health_degraded", settings.alert_on_health_degraded, "boolean", "notifications", commit=False)

        await self.db.commit()
        return settings
    
    async def update_api_settings(self, settings: APISettings) -> APISettings:
        """Update API settings."""
        await self.set_setting("api_keys_enabled", settings.api_keys_enabled, "boolean", "api", commit=False)
        await self.set_setting("webhook_enabled", settings.webhook_enabled, "boolean", "api", commit=False)
        await self.set_setting("webhook_url", settings.webhook_url, "string", "api", commit=False)
        await self.set_setting("documentation_public", settings.documentation_public, "boolean", "api", commit=False)
        await self.set_setting("cors_origins", settings.cors_origins, "json", "api", commit=False)
        
        await self.db.commit()
        return settings
    
    async def update_integration_settings(self, settings: IntegrationSettings) -> IntegrationSettings:
        """Update integration settings."""
        await self.set_setting("google_oauth_enabled", settings.google_oauth_enabled, "boolean", "integrations", commit=False)
        await self.set_setting("google_client_id", settings.google_client_id, "string", "integrations", commit=False)
        await self.set_setting("payment_provider", settings.payment_provider, "string", "integrations", commit=False)
        await self.set_setting("stripe_public_key", settings.stripe_public_key, "string", "integrations", commit=False)
        await self.set_setting("analytics_enabled", settings.analytics_enabled, "boolean", "integrations", commit=False)
        await self.set_setting("analytics_provider", settings.analytics_provider, "string", "integrations", commit=False)
        
        await self.db.commit()
        return settings
    
    async def update_ar_settings(self, settings: ARSettings) -> ARSettings:
        """Update AR settings."""
        await self.set_setting("mindar_max_features", settings.mindar_max_features, "integer", "ar", commit=False)
        await self.set_setting("marker_generation_enabled", settings.marker_generation_enabled, "boolean", "ar", commit=False)
        await self.set_setting("thumbnail_quality", settings.thumbnail_quality, "integer", "ar", commit=False)
        await self.set_setting("video_processing_enabled", settings.video_processing_enabled, "boolean", "ar", commit=False)
        await self.set_setting("default_ar_viewer_theme", settings.default_ar_viewer_theme, "string", "ar", commit=False)
        await self.set_setting("qr_code_expiration_days", settings.qr_code_expiration_days, "integer", "ar", commit=False)
        
        await self.db.commit()
        return settings

    async def update_backup_settings(self, settings: BackupSettings) -> BackupSettings:
        """Update database backup settings."""
        await self.set_setting("backup_enabled", settings.backup_enabled, "boolean", "backup", commit=False)
        await self.set_setting("backup_company_id", settings.backup_company_id, "integer", "backup", commit=False)
        await self.set_setting("backup_yd_folder", settings.backup_yd_folder, "string", "backup", commit=False)
        await self.set_setting("backup_schedule", settings.backup_schedule, "string", "backup", commit=False)
        await self.set_setting("backup_cron", settings.backup_cron, "string", "backup", commit=False)
        await self.set_setting("backup_retention_days", settings.backup_retention_days, "integer", "backup", commit=False)
        await self.set_setting("backup_max_copies", settings.backup_max_copies, "integer", "backup", commit=False)

        await self.db.commit()
        return settings
