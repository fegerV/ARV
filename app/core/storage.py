"""
Storage module for Vertex AR platform.

This module provides backward compatibility while redirecting to the new
storage provider abstraction. The old MinIO-specific functionality has been
removed in favor of a simplified local storage provider.
"""

from app.core.storage_providers import get_storage_provider, StorageProvider, LocalStorageProvider

# Re-export the main functions for backward compatibility
def get_storage_provider_instance() -> StorageProvider:
    """Get the current storage provider instance."""
    return get_storage_provider()

# Legacy compatibility - these functions are deprecated but maintained 
# for backward compatibility during the transition
async def save_file_to_storage(source_path: str, destination_path: str) -> str:
    """Save a file to storage using the configured provider."""
    provider = get_storage_provider()
    return await provider.save_file(source_path, destination_path)

async def get_file_from_storage(storage_path: str, local_path: str) -> bool:
    """Retrieve a file from storage using the configured provider."""
    provider = get_storage_provider()
    return await provider.get_file(storage_path, local_path)

async def delete_file_from_storage(storage_path: str) -> bool:
    """Delete a file from storage using the configured provider."""
    provider = get_storage_provider()
    return await provider.delete_file(storage_path)

async def check_file_exists(storage_path: str) -> bool:
    """Check if a file exists in storage using the configured provider."""
    provider = get_storage_provider()
    return await provider.file_exists(storage_path)

def get_public_file_url(storage_path: str) -> str:
    """Get public URL for a file in storage using the configured provider."""
    provider = get_storage_provider()
    return provider.get_public_url(storage_path)

async def get_storage_usage_stats(path: str = "") -> dict:
    """Get storage usage statistics using the configured provider."""
    provider = get_storage_provider()
    return await provider.get_usage_stats(path)