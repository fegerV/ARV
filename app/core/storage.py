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
            storage_provider = StorageProviderFactory.create_provider(
                "minio",
                {
                    "endpoint": settings.MINIO_ENDPOINT,
                    "access_key": settings.MINIO_ACCESS_KEY,
                    "secret_key": settings.MINIO_SECRET_KEY,
                    "secure": settings.MINIO_SECURE,
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
            storage_provider = StorageProviderFactory.create_provider(
                "yandex_disk",
                {
                    "oauth_token": settings.YANDEX_OAUTH_CLIENT_SECRET
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