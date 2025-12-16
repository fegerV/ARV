"""
Storage provider abstraction for Vertex AR platform.

This module provides a clean abstraction layer for storage operations,
currently supporting local file system storage with the ability to
extend to other providers in the future.
"""

import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class StorageProvider(ABC):
    """Abstract base class for storage providers."""
    
    @abstractmethod
    async def save_file(self, source_path: str, destination_path: str) -> str:
        """
        Save a file to storage.
        
        Args:
            source_path: Local path to the source file
            destination_path: Destination path in storage (relative)
            
        Returns:
            Public URL for accessing the file
        """
        pass
    
    @abstractmethod
    async def get_file(self, storage_path: str, local_path: str) -> bool:
        """
        Retrieve a file from storage.
        
        Args:
            storage_path: Path in storage (relative)
            local_path: Local path to save the file
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def delete_file(self, storage_path: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            storage_path: Path in storage (relative)
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def file_exists(self, storage_path: str) -> bool:
        """
        Check if a file exists in storage.
        
        Args:
            storage_path: Path in storage (relative)
            
        Returns:
            True if file exists, False otherwise
        """
        pass
    
    @abstractmethod
    def get_public_url(self, storage_path: str) -> str:
        """
        Get public URL for a file in storage.
        
        Args:
            storage_path: Path in storage (relative)
            
        Returns:
            Public URL for the file
        """
        pass
    
    @abstractmethod
    async def get_usage_stats(self, path: str = "") -> Dict[str, Any]:
        """
        Get storage usage statistics.
        
        Args:
            path: Path to analyze (relative, empty for root)
            
        Returns:
            Dictionary with usage statistics
        """
        pass


class LocalStorageProvider(StorageProvider):
    """Local file system storage provider."""
    
    def __init__(self, base_path: Optional[str] = None, public_url_base: Optional[str] = None):
        """
        Initialize local storage provider.
        
        Args:
            base_path: Base path for storage files
            public_url_base: Base URL for public access
        """
        self.base_path = Path(base_path or settings.LOCAL_STORAGE_PATH)
        self.public_url_base = public_url_base or settings.LOCAL_STORAGE_PUBLIC_URL
        
        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        logger.info("local_storage_provider_initialized", 
                   base_path=str(self.base_path),
                   public_url_base=self.public_url_base)
    
    def _get_full_path(self, storage_path: str) -> Path:
        """Get full file system path for a storage path."""
        # Ensure storage_path is relative and doesn't escape base directory
        storage_path = storage_path.lstrip('/')
        return self.base_path / storage_path
    
    async def save_file(self, source_path: str, destination_path: str) -> str:
        """Save a file to local storage."""
        source = Path(source_path)
        destination = self._get_full_path(destination_path)
        
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")
        
        # Create destination directory if needed
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file
        shutil.copy2(source, destination)
        
        logger.info("file_saved_to_local_storage", 
                   source_path=str(source),
                   destination_path=str(destination))
        
        return self.get_public_url(destination_path)
    
    async def get_file(self, storage_path: str, local_path: str) -> bool:
        """Retrieve a file from local storage."""
        source = self._get_full_path(storage_path)
        destination = Path(local_path)
        
        if not source.exists():
            return False
        
        # Create destination directory if needed
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy file
        shutil.copy2(source, destination)
        
        logger.info("file_retrieved_from_local_storage",
                   storage_path=storage_path,
                   local_path=str(destination))
        
        return True
    
    async def delete_file(self, storage_path: str) -> bool:
        """Delete a file from local storage."""
        file_path = self._get_full_path(storage_path)
        
        if not file_path.exists():
            return False
        
        try:
            if file_path.is_file():
                file_path.unlink()
            elif file_path.is_dir():
                shutil.rmtree(file_path)
            
            logger.info("file_deleted_from_local_storage", storage_path=storage_path)
            return True
        except Exception as e:
            logger.error("failed_to_delete_file_from_local_storage", 
                        storage_path=storage_path, error=str(e))
            return False
    
    async def file_exists(self, storage_path: str) -> bool:
        """Check if a file exists in local storage."""
        file_path = self._get_full_path(storage_path)
        return file_path.exists()
    
    def get_public_url(self, storage_path: str) -> str:
        """Get public URL for a file in local storage."""
        # Normalize path and remove leading slash
        storage_path = storage_path.lstrip('/')
        return f"{self.public_url_base.rstrip('/')}/{storage_path}"
    
    async def get_usage_stats(self, path: str = "") -> Dict[str, Any]:
        """Get storage usage statistics for local storage."""
        target_path = self._get_full_path(path)
        
        if not target_path.exists():
            return {
                "total_files": 0,
                "total_size_bytes": 0,
                "total_size_mb": 0,
                "path": str(target_path),
                "exists": False
            }
        
        total_size = 0
        file_count = 0
        
        if target_path.is_file():
            total_size = target_path.stat().st_size
            file_count = 1
        else:
            for item in target_path.rglob("*"):
                if item.is_file():
                    total_size += item.stat().st_size
                    file_count += 1
        
        return {
            "total_files": file_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "path": str(target_path),
            "exists": True
        }


# Global storage provider instance
_storage_provider: Optional[StorageProvider] = None


def get_storage_provider() -> StorageProvider:
    """
    Get the configured storage provider instance.
    
    Returns:
        StorageProvider: The configured storage provider
    """
    global _storage_provider
    
    if _storage_provider is None:
        _storage_provider = LocalStorageProvider()
        logger.info("storage_provider_created", provider="LocalStorageProvider")
    
    return _storage_provider


def reset_storage_provider() -> None:
    """Reset the global storage provider instance (for testing)."""
    global _storage_provider
    _storage_provider = None