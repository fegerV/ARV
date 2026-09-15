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
        default="",
        description="Database connection URL. Must be set via environment variable."
    )
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO: bool = False
    
    # Security
    SECRET_KEY: str = Field(min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Dedicated secrets. Each falls back to SECRET_KEY when unset so that
    # existing deployments keep working, but they SHOULD be set separately so
    # that leaking one secret does not compromise the others.
    SESSION_SECRET_KEY: str = ""       # signs browser session cookies
    TOKEN_ENCRYPTION_KEY: str = ""     # encrypts stored OAuth tokens (Fernet)
    MEDIA_URL_SECRET: str = ""         # signs Yandex Disk proxy URLs

    # Legacy unsalted SHA-256 password hashes are only accepted while accounts
    # are being migrated. They MUST be disabled in production; when disabled,
    # such accounts simply fail to authenticate (forcing a password reset).
    ALLOW_LEGACY_PASSWORD_HASHES: bool = False

    # SameSite policy for the ``access_token`` session cookie.
    #   "lax"    — default: cookie is sent on top-level GET navigations, which
    #              keeps "open the admin panel from a link" working, and still
    #              blocks cross-site POST/iframe/subresource requests.
    #   "strict" — tightest: cookie is never sent on cross-site navigations, so
    #              users arriving via an external link land logged-out (they
    #              must refresh). Recommended once UX impact is acceptable.
    COOKIE_SAMESITE: str = "lax"

    @property
    def session_secret(self) -> str:
        """Secret used to sign browser session cookies."""
        return self.SESSION_SECRET_KEY or self.SECRET_KEY

    @property
    def token_encryption_secret(self) -> str:
        """Secret used to derive the token-encryption key."""
        return self.TOKEN_ENCRYPTION_KEY or self.SECRET_KEY

    @property
    def media_url_secret(self) -> str:
        """Secret used to sign media proxy URLs."""
        return self.MEDIA_URL_SECRET or self.SECRET_KEY
    
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
    TELEGRAM_PROXY_URL: str = ""
    
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

    # ------------------------------------------------------------------
    # Backup / disaster recovery (see docs/BACKUP_AND_RECOVERY.md)
    # ------------------------------------------------------------------
    # Local staging directory where dumps are assembled before shipping.
    BACKUP_STAGING_DIR: str = "/var/backups/arv"

    # Encryption of database dumps. When AGE_RECIPIENT is set, the dump is
    # encrypted with `age` before it leaves the host. The matching private key
    # MUST NOT be stored on this server (see docs, section "Encryption").
    BACKUP_AGE_RECIPIENT: str = ""
    BACKUP_AGE_BINARY: str = "age"
    # Private key used to DECRYPT during a restore/drill. Deliberately a
    # separate setting: the encryption recipient is public and may live on the
    # production host, while the identity must be mounted only for the short
    # duration of a restore (see docs, section "Encryption").
    BACKUP_AGE_IDENTITY_FILE: str = ""

    # Secondary, independent off-site target (a DIFFERENT provider than the one
    # holding production media, so a single account compromise cannot destroy
    # both the primary data and its backup). Any rclone remote works.
    BACKUP_SECONDARY_RCLONE_REMOTE: str = ""
    BACKUP_RCLONE_BINARY: str = "rclone"

    # Media backup via restic (deduplicated, encrypted, incremental snapshots).
    BACKUP_MEDIA_ENABLED: bool = False
    BACKUP_RESTIC_BINARY: str = "restic"
    BACKUP_RESTIC_REPOSITORY: str = ""
    BACKUP_RESTIC_PASSWORD_FILE: str = ""
    BACKUP_MEDIA_PATHS: str = ""  # comma-separated; defaults to STORAGE_BASE_PATH

    # External dead-man's-switch. Metric-based alerting cannot detect a host
    # that is entirely down, because the metrics simply stop arriving.
    BACKUP_HEARTBEAT_URL: str = ""

    # GFS retention (grandfather-father-son).
    BACKUP_KEEP_DAILY: int = 7
    BACKUP_KEEP_WEEKLY: int = 4
    BACKUP_KEEP_MONTHLY: int = 12
    BACKUP_KEEP_YEARLY: int = 3

    # Verify a restored copy at least this often; alert when overdue.
    BACKUP_MAX_AGE_HOURS: int = 26
    # The secrets archive (class A3) is weekly, so the daily limit would flag it
    # as stale six days out of seven. Kept as its own knob rather than loosening
    # the daily rule for the jobs that actually run daily.
    BACKUP_SECRETS_MAX_AGE_HOURS: int = 8 * 24
    BACKUP_DRILL_MAX_AGE_DAYS: int = 31

    # PostgreSQL client binaries used by the restore/drill path. They are
    # resolved by name so the host's own pg_dump/pg_restore version is used
    # (a version mismatch with the server is the classic silent restore break).
    BACKUP_PG_RESTORE_BINARY: str = "pg_restore"
    BACKUP_PSQL_BINARY: str = "psql"
    # Parallel restore workers; -j requires the custom format, which is exactly
    # why the dump uses -Fc.
    BACKUP_RESTORE_JOBS: int = 4
    # Prefix for the throwaway database created by the restore drill.
    BACKUP_DRILL_DB_PREFIX: str = "arv_drill"

    @property
    def backup_media_paths(self) -> list[str]:
        """Filesystem paths covered by the media backup."""
        raw = (self.BACKUP_MEDIA_PATHS or "").strip()
        if raw:
            return [p.strip() for p in raw.split(",") if p.strip()]
        return [self.STORAGE_BASE_PATH]

    @property
    def encryption_enabled(self) -> bool:
        """True when dumps are encrypted with age before leaving the host."""
        return bool(self.BACKUP_AGE_RECIPIENT)

    @property
    def secondary_target_enabled(self) -> bool:
        """True when a second, independent off-site target is configured."""
        return bool(self.BACKUP_SECONDARY_RCLONE_REMOTE)

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

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate DATABASE_URL is properly configured."""
        if not v:
            raise ValueError("DATABASE_URL must be set")
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate SECRET_KEY is configured with sufficient length."""
        if not v:
            raise ValueError("SECRET_KEY must be set via environment variable and be at least 32 characters long.")
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters in all environments.")
        return v

    def validate_sensitive_defaults(self) -> None:
        """Ensure insecure defaults are not used."""
        # Always validate SQLite regardless of environment
        if self.DATABASE_URL and "sqlite" in self.DATABASE_URL.lower():
            raise ValueError("SQLite is not allowed. Use PostgreSQL for all environments.")

        # Validate SECRET_KEY minimum length in all environments
        if len(self.SECRET_KEY) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters in all environments.")

        # In production, enforce additional security requirements
        if not self.is_production:
            return

        if not self.ADMIN_DEFAULT_PASSWORD:
            raise ValueError("ADMIN_DEFAULT_PASSWORD must be set in production.")

        if self.REDIS_URL and "localhost" in self.REDIS_URL and "redis://" in self.REDIS_URL:
            raise ValueError("REDIS_URL must not use plain localhost in production. Use TLS or internal network.")

        if "gmail.com" in self.SMTP_HOST.lower() and not self.SMTP_PASSWORD:
            raise ValueError("SMTP_PASSWORD must be set when using Gmail SMTP in production.")


# Global settings instance
settings = Settings()

@lru_cache
def get_settings() -> Settings:
    return Settings()
