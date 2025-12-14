"""
Simplified Storage API for Vertex AR platform.

This module provides simplified storage endpoints focused on local storage only.
All MinIO/Yandex Disk functionality has been removed.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from psutil import disk_usage
import structlog

from app.core.database import get_db
from app.core.config import settings
from app.models.company import Company
from app.models.project import Project
from app.models.ar_content import ARContent
from app.models.video import Video
from app.schemas.storage import StorageUsageStats, StorageHealthStatus

logger = structlog.get_logger()

router = APIRouter()


class LocalStorageAdapter:
    """Simplified local storage adapter."""
    
    def __init__(self, base_path: Optional[str] = None, public_url_base: Optional[str] = None):
        self.base_path = Path(base_path or settings.LOCAL_STORAGE_PATH)
        self.public_url_base = public_url_base or settings.LOCAL_STORAGE_PUBLIC_URL
        
        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)
    
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
        full_path = self.base_path / file_path
        
        # Create directory if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        with open(full_path, 'wb') as f:
            f.write(file_content)
        
        return self.get_public_url(file_path)
    
    def get_file(self, file_path: str) -> bytes:
        """
        Get file content from local storage.
        
        Args:
            file_path: Relative path to the file
            
        Returns:
            File content as bytes
        """
        full_path = self.base_path / file_path
        
        if not full_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
        with open(full_path, 'rb') as f:
            return f.read()
    
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
            return False
        
        try:
            if full_path.is_file():
                full_path.unlink()
            elif full_path.is_dir():
                shutil.rmtree(full_path)
            return True
        except Exception:
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
        total_size = 0
        file_count = 0
        
        if self.base_path.exists():
            for item in self.base_path.rglob("*"):
                if item.is_file():
                    total_size += item.stat().st_size
                    file_count += 1
        
        return {
            "total_files": file_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "base_path": str(self.base_path)
        }


# Global storage adapter instance
_storage_adapter: Optional[LocalStorageAdapter] = None


def get_storage_adapter() -> LocalStorageAdapter:
    """Get the storage adapter instance."""
    global _storage_adapter
    if _storage_adapter is None:
        _storage_adapter = LocalStorageAdapter()
    return _storage_adapter


@router.get("/storage/health", response_model=StorageHealthStatus)
async def get_storage_health():
    """
    Get storage health status.
    
    Returns information about disk space and storage availability.
    """
    try:
        base_path = Path(settings.LOCAL_STORAGE_PATH)
        
        # Ensure directory exists
        base_path.mkdir(parents=True, exist_ok=True)
        
        # Get disk usage - use parent directory if base_path doesn't exist yet
        disk_path = base_path if base_path.exists() else base_path.parent
        disk_info = disk_usage(disk_path)
        
        # Get storage usage
        adapter = get_storage_adapter()
        storage_usage = adapter.get_storage_usage()
        
        return StorageHealthStatus(
            status="healthy",
            base_path=str(base_path),
            total_disk_space_gb=round(disk_info.total / (1024**3), 2),
            used_disk_space_gb=round(disk_info.used / (1024**3), 2),
            free_disk_space_gb=round(disk_info.free / (1024**3), 2),
            disk_usage_percent=round((disk_info.used / disk_info.total) * 100, 2),
            storage_files_count=storage_usage["total_files"],
            storage_size_mb=storage_usage["total_size_mb"],
            is_writable=os.access(base_path, os.W_OK)
        )
        
    except Exception as e:
        import traceback
        error_details = f"Failed to get storage health: {str(e)}\n{traceback.format_exc()}"
        logger.error("storage_health_error", error=str(e), traceback=traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_details)


@router.get("/storage/usage")
async def get_storage_usage(
    company_id: Optional[int] = Query(None, description="Filter by company ID"),
    file_type: Optional[str] = Query(None, description="Filter by file type: images, videos, all"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed storage usage statistics.
    
    Returns usage breakdown by companies and file types.
    """
    try:
        adapter = get_storage_adapter()
        
        # Base usage stats
        base_stats = adapter.get_storage_usage()
        
        result = {
            "overall": base_stats,
            "by_companies": [],
            "by_file_types": {
                "images": {"count": 0, "size_bytes": 0, "size_mb": 0},
                "videos": {"count": 0, "size_bytes": 0, "size_mb": 0},
                "other": {"count": 0, "size_bytes": 0, "size_mb": 0}
            }
        }
        
        # Get companies with their content
        query = select(Company).where(Company.status == "active")
        if company_id:
            query = query.where(Company.id == company_id)
            
        companies_result = await db.execute(query)
        companies = companies_result.scalars().all()
        
        for company in companies:
            # Get projects for this company
            projects_query = select(Project).where(Project.company_id == company.id)
            projects_result = await db.execute(projects_query)
            projects = projects_result.scalars().all()
            
            company_stats = {
                "company_id": company.id,
                "company_name": company.name,
                "projects_count": len(projects),
                "ar_content_count": 0,
                "videos_count": 0,
                "estimated_size_mb": 0
            }
            
            # Get AR content for all projects
            for project in projects:
                ar_content_query = select(ARContent).where(ARContent.project_id == project.id)
                ar_content_result = await db.execute(ar_content_query)
                ar_contents = ar_content_result.scalars().all()
                
                company_stats["ar_content_count"] += len(ar_contents)
                
                # Get videos for AR content
                for ar_content in ar_contents:
                    videos_query = select(Video).where(Video.ar_content_id == ar_content.id)
                    videos_result = await db.execute(videos_query)
                    videos = videos_result.scalars().all()
                    
                    company_stats["videos_count"] += len(videos)
                    
                    # Estimate size (rough calculation)
                    for video in videos:
                        if hasattr(video, 'size') and video.size:
                            company_stats["estimated_size_mb"] += video.size / (1024 * 1024)
            
            result["by_companies"].append(company_stats)
        
        # Analyze file types in storage
        if adapter.base_path.exists():
            for file_path in adapter.base_path.rglob("*"):
                if file_path.is_file():
                    file_size = file_path.stat().st_size
                    file_ext = file_path.suffix.lower()
                    
                    if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                        result["by_file_types"]["images"]["count"] += 1
                        result["by_file_types"]["images"]["size_bytes"] += file_size
                    elif file_ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
                        result["by_file_types"]["videos"]["count"] += 1
                        result["by_file_types"]["videos"]["size_bytes"] += file_size
                    else:
                        result["by_file_types"]["other"]["count"] += 1
                        result["by_file_types"]["other"]["size_bytes"] += file_size
        
        # Convert bytes to MB for file types
        for file_type in result["by_file_types"]:
            stats = result["by_file_types"][file_type]
            stats["size_mb"] = round(stats["size_bytes"] / (1024 * 1024), 2)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get storage usage: {str(e)}")