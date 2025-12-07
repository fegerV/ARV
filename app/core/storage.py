from pathlib import Path
from datetime import timedelta
from app.core.config import settings
from app.services.storage.factory import StorageProviderFactory

# Storage provider instance - initialized lazily
storage_provider = None

def get_storage_provider():
    """Get or initialize the storage provider."""
    global storage_provider
    if storage_provider is None:
        initialize_storage_provider()
    return storage_provider

def initialize_storage_provider():
    """Initialize storage provider based on configuration."""
    global storage_provider
    
    if settings.STORAGE_TYPE == "local":
        storage_provider = StorageProviderFactory.create_provider(
            "local_disk",
            {
                "base_path": settings.STORAGE_BASE_PATH
            }
        )
    elif settings.STORAGE_TYPE == "minio":
        try:
            # Validate required MinIO settings
            if not all([settings.MINIO_ENDPOINT, settings.MINIO_ACCESS_KEY, settings.MINIO_SECRET_KEY]):
                raise ValueError("Missing required MinIO configuration: endpoint, access_key, or secret_key")
            
            storage_provider = StorageProviderFactory.create_provider(
                "minio",
                {
                    "endpoint": settings.MINIO_ENDPOINT,
                    "access_key": settings.MINIO_ACCESS_KEY,
                    "secret_key": settings.MINIO_SECRET_KEY,
                    "secure": settings.MINIO_SECURE,
                    "region": settings.MINIO_REGION,
                    "bucket_name": settings.MINIO_BUCKET_NAME,
                }
            )
        except Exception as e:
            print(f"Warning: Failed to initialize MinIO provider: {e}")
            # Fall back to local storage
            storage_provider = StorageProviderFactory.create_provider(
                "local_disk",
                {
                    "base_path": settings.STORAGE_BASE_PATH
                }
            )
    elif settings.STORAGE_TYPE == "yandex_disk":
        try:
            # Validate required Yandex Disk settings
            if not settings.YANDEX_DISK_OAUTH_TOKEN:
                raise ValueError("Missing required Yandex Disk configuration: oauth_token")
            
            storage_provider = StorageProviderFactory.create_provider(
                "yandex_disk",
                {
                    "oauth_token": settings.YANDEX_DISK_OAUTH_TOKEN,
                    "base_path": settings.YANDEX_DISK_BASE_PATH
                }
            )
        except Exception as e:
            print(f"Warning: Failed to initialize Yandex Disk provider: {e}")
            # Fall back to local storage
            storage_provider = StorageProviderFactory.create_provider(
                "local_disk",
                {
                    "base_path": settings.STORAGE_BASE_PATH
                }
            )
    else:
        # Default to local storage
        storage_provider = StorageProviderFactory.create_provider(
            "local_disk",
            {
                "base_path": settings.STORAGE_BASE_PATH
            }
        )