from typing import Any
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application configuration settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Application
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # Default to development for local setup
    LOG_LEVEL: str = "INFO"
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"
    
    # Project info
    PROJECT_NAME: str = "V-Portal Backend"
    VERSION: str = "2.0.0"
    
    # Database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./test_vertex_ar.db"
    )
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO: bool = False
    
    # Security
    SECRET_KEY: str = Field(min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # CORS
    CORS_ORIGINS: Any = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:3002",
            "http://localhost:3003",
            "http://localhost:3004",
            "http://localhost:8000",
        ]
    )

    PUBLIC_URL: str = Field(default="http://localhost:8000")

    # SSL / HTTPS (сертификаты в папке ssl/, порты проброшены)
    SSL_KEYFILE: str = ""   # путь к privkey.pem (например ssl/privkey.pem)
    SSL_CERTFILE: str = ""  # путь к fullchain.pem (например ssl/fullchain.pem)

    @property
    def ssl_enabled(self) -> bool:
        """True, если заданы оба пути к сертификатам и файлы существуют."""
        if not self.SSL_KEYFILE or not self.SSL_CERTFILE:
            return False
        from pathlib import Path
        return Path(self.SSL_KEYFILE).exists() and Path(self.SSL_CERTFILE).exists()

    # Media (относительные пути для CI/локальной разработки; в Docker задаются через env)
    MEDIA_ROOT: str = "./storage/content"
    TEMPLATES_DIR: str = "./templates"
    STATIC_DIR: str = "./static"
    
    # Storage
    # Default to ./storage relative to project root, or /tmp/storage if running in container
    STORAGE_BASE_PATH: str = "./storage"
    
    # Local Storage
    LOCAL_STORAGE_PATH: str = "./storage"
    LOCAL_STORAGE_PUBLIC_URL: str = "http://localhost:8000/storage"
    
    # File storage configuration
    ALLOWED_FILE_EXTENSIONS_PHOTO: list[str] = ["jpeg", "jpg", "png"]
    ALLOWED_FILE_EXTENSIONS_VIDEO: list[str] = ["mp4", "webm", "mov"]
    MAX_FILE_SIZE_PHOTO: int = 10 * 1024 * 1024  # 10MB
    MAX_FILE_SIZE_VIDEO: int = 100 * 1024 * 1024  # 100MB
    
    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@vertexar.com"
    SMTP_FROM_NAME: str = "V-Portal Platform"
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_ADMIN_CHAT_ID: str = ""
    
    # Admin
    ADMIN_EMAIL: str = "admin@vertexar.com"
    ADMIN_DEFAULT_PASSWORD: str
    ADMIN_FRONTEND_URL: str = "http://localhost:3000"
    
    # Monitoring
    SENTRY_DSN: str = ""

    # Admin: просмотр логов (страница /admin/logs)
    # LOG_FILE — путь к файлу логов (если задан и файл есть, читаем из него)
    # Иначе пробуем journalctl -u LOG_JOURNALCTL_UNIT (нужны права на чтение journal)
    LOG_FILE: str = ""
    LOG_JOURNALCTL_UNIT: str = "arv"
    LOG_MAX_LINES: int = 500
    
    # Android App Links (for /.well-known/assetlinks.json)
    ANDROID_APP_PACKAGE: str = "ru.neuroimagen.arviewer"
    # SHA-256 cert fingerprints (comma-separated), e.g. from Play Console App Signing
    ANDROID_APP_SHA256_FINGERPRINTS: str = ""
    # iOS: ссылка на приложение в App Store (для страницы /view/; если пусто — кнопка не показывается)
    APP_STORE_URL: str = ""
    PLAY_STORE_URL: str = "https://play.google.com/store/apps/details?id=ru.neuroimagen.arviewer"
    RUSTORE_URL: str = "https://www.rustore.ru/catalog/app/ru.neuroimagen.arviewer"
    APP_GALLERY_URL: str = "https://appgallery.huawei.com/#/app/C117404839"

    # Yandex OAuth (for Yandex Disk storage)
    YANDEX_OAUTH_CLIENT_ID: str = ""
    YANDEX_OAUTH_CLIENT_SECRET: str = ""

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """Parse CORS origins from comma-separated string to list."""
        if isinstance(v, list):
            return [origin.strip() if isinstance(origin, str) else origin for origin in v]
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_flag(cls, v: Any) -> bool:
        """Accept legacy string values like 'release' or 'production' as False."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            normalized = v.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "dev"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "prod", "production"}:
                return False
        return bool(v)

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as list."""
        return self.CORS_ORIGINS

    def validate_sensitive_defaults(self) -> None:
        """Ensure insecure defaults are not used."""
        if not self.is_production:
            return

        if len(self.SECRET_KEY) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters in production.")

        if not self.ADMIN_DEFAULT_PASSWORD:
            raise ValueError("ADMIN_DEFAULT_PASSWORD must be set in production.")

        if "sqlite" in self.DATABASE_URL.lower():
            raise ValueError("SQLite is not allowed in production. Use PostgreSQL.")

        if self.REDIS_URL and "localhost" in self.REDIS_URL and "redis://" in self.REDIS_URL:
            raise ValueError("REDIS_URL must not use plain localhost in production. Use TLS or internal network.")

        if "gmail.com" in self.SMTP_HOST.lower() and not self.SMTP_PASSWORD:
            raise ValueError("SMTP_PASSWORD must be set when using Gmail SMTP in production.")


# Global settings instance
settings = Settings()

@lru_cache
def get_settings() -> Settings:
    return Settings()
