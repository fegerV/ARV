from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class SettingCategory(str, Enum):
    GENERAL = "general"
    SECURITY = "security"
    STORAGE = "storage"
    NOTIFICATIONS = "notifications"
    API = "api"
    INTEGRATIONS = "integrations"
    AR = "ar"
    BACKUP = "backup"

class SettingDataType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    JSON = "json"

class SystemSettingsBase(BaseModel):
    key: str = Field(..., min_length=1, max_length=100)
    value: Optional[str] = None
    data_type: SettingDataType = SettingDataType.STRING
    category: SettingCategory = SettingCategory.GENERAL
    description: Optional[str] = None
    is_public: bool = False

class SystemSettingsCreate(SystemSettingsBase):
    pass

class SystemSettingsUpdate(BaseModel):
    value: Optional[str] = None
    data_type: Optional[SettingDataType] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None

class SystemSettingsResponse(SystemSettingsBase):
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Settings group schemas for frontend
class GeneralSettings(BaseModel):
    site_title: str = "Vertex AR B2B Platform"
    admin_email: str = "admin@vertexar.com"
    site_description: str = "B2B SaaS platform for creating AR content based on image recognition (NFT markers)"
    maintenance_mode: bool = False
    timezone: str = "UTC"
    language: str = "en"
    default_subscription_years: int = 1
    
class SecuritySettings(BaseModel):
    password_min_length: int = 8
    session_timeout: int = 60
    require_2fa: bool = False
    max_login_attempts: int = 5
    lockout_duration: int = 300
    api_rate_limit: int = 100
    
class StorageSettings(BaseModel):
    default_storage: str = "local"
    max_file_size: int = 100
    cdn_enabled: bool = False
    cdn_url: Optional[str] = None
    backup_enabled: bool = True
    backup_retention_days: int = 30
    
class NotificationSettings(BaseModel):
    email_enabled: bool = True
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_from_email: str = "noreply@vertexar.com"
    telegram_enabled: bool = False
    telegram_bot_token: Optional[str] = None
    telegram_admin_chat_id: Optional[str] = None
    
class APISettings(BaseModel):
    api_keys_enabled: bool = True
    webhook_enabled: bool = False
    webhook_url: Optional[str] = None
    documentation_public: bool = True
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
class IntegrationSettings(BaseModel):
    google_oauth_enabled: bool = False
    google_client_id: Optional[str] = None
    payment_provider: str = "stripe"
    stripe_public_key: Optional[str] = None
    analytics_enabled: bool = False
    analytics_provider: str = "google"
    
class ARSettings(BaseModel):
    mindar_max_features: int = 1000
    marker_generation_enabled: bool = True
    thumbnail_quality: int = 80
    video_processing_enabled: bool = True
    default_ar_viewer_theme: str = "default"
    qr_code_expiration_days: int = 365
    
class BackupSettings(BaseModel):
    """Database backup configuration."""

    backup_enabled: bool = False
    backup_company_id: Optional[int] = None
    backup_yd_folder: str = "backups"
    backup_schedule: str = "daily"
    backup_cron: str = "0 3 * * *"
    backup_retention_days: int = 30
    backup_max_copies: int = 30


class AllSettings(BaseModel):
    general: GeneralSettings
    security: SecuritySettings
    storage: StorageSettings
    notifications: NotificationSettings
    api: APISettings
    integrations: IntegrationSettings
    ar: ARSettings
    backup: BackupSettings