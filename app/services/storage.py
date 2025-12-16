"""
Simplified Storage Service for Vertex AR platform.

This module provides a simplified storage interface with only LocalStorageAdapter.
All MinIO/Yandex Disk functionality has been removed.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class LocalStorageAdapter:
    """
    Simplified local storage adapter.
    
    Provides basic file operations for local file system storage.
    """
    
    def __init__(self, base_path: Optional[str] = None, public_url_base: Optional[str] = None):
        """
        Initialize local storage adapter.
        
        Args:
            base_path: Base path for storage files
            public_url_base: Base URL for public access
        """
        self.base_path = Path(base_path or settings.LOCAL_STORAGE_PATH)
        self.public_url_base = public_url_base or settings.LOCAL_STORAGE_PUBLIC_URL
        
        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        logger.info("local_storage_adapter_initialized", 
                   base_path=str(self.base_path),
                   public_url_base=self.public_url_base)
    
    def save_file(self, file_path: str, file_content: bytes, content_type: str = None) -> str:
        """
        Save a file to local storage.
        
        Args:
            file_path: Relative path where to save the file
            file_content: File content as bytes
            content_type: MIME type (optional, for future use)
            
        Returns:
            Public URL for accessing the file
        """
        try:
            full_path = self.base_path / file_path
            
            # Create directory if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            with open(full_path, 'wb') as f:
                f.write(file_content)
            
            logger.info("file_saved_to_local_storage", 
                       file_path=file_path,
                       full_path=str(full_path),
                       size_bytes=len(file_content))
            
            return self.get_public_url(file_path)
            
        except Exception as e:
            logger.error("failed_to_save_file_to_local_storage",
                        file_path=file_path,
                        error=str(e))
            raise
    
    def get_file(self, file_path: str) -> bytes:
        """
        Get file content from local storage.
        
        Args:
            file_path: Relative path to the file
            
        Returns:
            File content as bytes
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        full_path = self.base_path / file_path
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            with open(full_path, 'rb') as f:
                content = f.read()
            
            logger.info("file_retrieved_from_local_storage",
                       file_path=file_path,
                       size_bytes=len(content))
            
            return content
            
        except Exception as e:
            logger.error("failed_to_retrieve_file_from_local_storage",
                        file_path=file_path,
                        error=str(e))
            raise
    
    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from local storage.
        
        Args:
            file_path: Relative path to the file
            
        Returns:
            True if deleted, False if file didn't exist
        """
        full_path = self.base_path / file_path
        
        if not full_path.exists():
            logger.warning("file_not_found_for_deletion", file_path=file_path)
            return False
        
        try:
            if full_path.is_file():
                full_path.unlink()
            elif full_path.is_dir():
                shutil.rmtree(full_path)
            
            logger.info("file_deleted_from_local_storage", file_path=file_path)
            return True
            
        except Exception as e:
            logger.error("failed_to_delete_file_from_local_storage",
                        file_path=file_path,
                        error=str(e))
            return False
    
    def get_public_url(self, file_path: str) -> str:
        """
        Get public URL for a file.
        
        Args:
            file_path: Relative path to the file
            
        Returns:
            Public URL
        """
        normalized_path = file_path.lstrip('/')
        return f"{self.public_url_base.rstrip('/')}/{normalized_path}"
    
    def get_storage_usage(self) -> Dict[str, Any]:
        """
        Get storage usage statistics.
        
        Returns:
            Dictionary with usage statistics
        """
        try:
            total_size = 0
            file_count = 0
            
            if self.base_path.exists():
                for item in self.base_path.rglob("*"):
                    if item.is_file():
                        total_size += item.stat().st_size
                        file_count += 1
            
            stats = {
                "total_files": file_count,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "base_path": str(self.base_path),
                "exists": self.base_path.exists()
            }
            
            logger.info("storage_usage_stats_calculated", **stats)
            return stats
            
        except Exception as e:
            logger.error("failed_to_calculate_storage_usage", error=str(e))
            return {
                "total_files": 0,
                "total_size_bytes": 0,
                "total_size_mb": 0,
                "base_path": str(self.base_path),
                "exists": False
            }


# Global storage adapter instance
_storage_adapter: Optional[LocalStorageAdapter] = None


def get_storage_adapter() -> LocalStorageAdapter:
    """
    Get the storage adapter instance.
    
    Returns:
        LocalStorageAdapter: The storage adapter instance
    """
    global _storage_adapter
    
    if _storage_adapter is None:
        _storage_adapter = LocalStorageAdapter()
        logger.info("storage_adapter_created", adapter="LocalStorageAdapter")
    
    return _storage_adapter


def reset_storage_adapter() -> None:
    """
    Reset the global storage adapter instance (for testing).
    """
    global _storage_adapter
    _storage_adapter = None
    logger.info("storage_adapter_reset")