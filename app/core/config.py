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

    # Application
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    LOG_LEVEL: str = "INFO"
    
    # Project info
    PROJECT_NAME: str = "Vertex AR with Mind AR"
    VERSION: str = "2.0.0"
    API_V1_PREFIX: str = "/api"
    
    # Mind AR
    MINDAR_COMPILER_PATH: str = "npx mind-ar-js-compiler"
    MINDAR_MAX_FEATURES: int = 1000
    
    # Allowed origins (optional, alongside CORS_ORIGINS)
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://vertex_ar:password@localhost:5432/vertex_ar"
    )
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO: bool = False
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_MAX_CONNECTIONS: int = 50
    
    # Security
    SECRET_KEY: str = Field(default="change-this-to-a-secure-random-key-min-32-chars")
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
    CORS_ALLOW_CREDENTIALS: bool = True
    
    # Storage
    STORAGE_TYPE: str = "local"  # local, minio, yandex_disk
    STORAGE_BASE_PATH: str = "/app/storage/content"
    
    # MinIO
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_NAME: str = "vertex-ar"
    # Separate buckets (optional)
    MINIO_BUCKET_VIDEOS: str = "ar-videos"
    MINIO_BUCKET_MARKERS: str = "ar-markers"
    MINIO_BUCKET_THUMBNAILS: str = "ar-thumbnails"
    MINIO_SECURE: bool = False
    
    # Yandex Disk
    YANDEX_OAUTH_CLIENT_ID: str = ""
    YANDEX_OAUTH_CLIENT_SECRET: str = ""
    YANDEX_OAUTH_REDIRECT_URI: str = "http://localhost:8000/api/oauth/yandex/callback"
    
    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@vertexar.com"
    SMTP_FROM_NAME: str = "Vertex AR Platform"
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_ADMIN_CHAT_ID: str = ""
    
    # Admin
    ADMIN_EMAIL: str = "admin@vertexar.com"
    ADMIN_DEFAULT_PASSWORD: str = "ChangeMe123!"
    ADMIN_FRONTEND_URL: str = "http://localhost:3000"
    
    # Celery
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/0")
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_TASK_TIME_LIMIT: int = 300  # 5 minutes
    
    # Storage
    STORAGE_PROVIDER: str = Field(default="local")  # local, minio, yandex_disk
    STORAGE_ENABLE_CACHING: bool = Field(default=True)
    STORAGE_CACHE_TTL: int = Field(default=3600)  # 1 hour
    
    # Local Storage
    LOCAL_STORAGE_PATH: str = Field(default="/app/storage/content")
    LOCAL_STORAGE_PUBLIC_URL: str = Field(default="http://localhost:8000/storage")
    
    # MinIO Configuration
    MINIO_ENDPOINT: str = Field(default="localhost:9000")
    MINIO_ROOT_USER: str = Field(default="minioadmin")
    MINIO_ROOT_PASSWORD: str = Field(default="minioadmin")
    MINIO_BUCKET_NAME: str = Field(default="vertex-ar")
    MINIO_USE_SSL: bool = Field(default=False)
    MINIO_REGION: str = Field(default="us-east-1")
    
    # Yandex Disk Configuration
    YANDEX_OAUTH_TOKEN: str = Field(default="")
    YANDEX_APP_ID: str = Field(default="")
    YANDEX_ROOT_FOLDER: str = Field(default="/VertexAR")
    
    # Monitoring
    SENTRY_DSN: str = ""
    PROMETHEUS_MULTIPROC_DIR: str = "/tmp/prometheus_multiproc"
    
    # Backup
    BACKUP_S3_ENDPOINT: str = ""
    BACKUP_S3_ACCESS_KEY: str = ""
    BACKUP_S3_SECRET_KEY: str = ""
    BACKUP_S3_BUCKET: str = "vertex-ar-backups"
    BACKUP_RETENTION_DAYS: int = 30

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """Parse CORS origins from comma-separated string to list."""
        if isinstance(v, list):
            return [origin.strip() if isinstance(origin, str) else origin for origin in v]
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as list."""
        return self.CORS_ORIGINS


# Global settings instance
settings = Settings()

@lru_cache
def get_settings() -> Settings:
    return Settings()
