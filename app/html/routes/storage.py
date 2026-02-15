from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pathlib import Path
from typing import Tuple
import shutil
import structlog
import traceback

from app.html.deps import get_html_db
from app.api.routes.auth import get_current_user_optional
from app.html.filters import datetime_format
from app.models.company import Company
from app.models.project import Project
from app.models.ar_content import ARContent
from app.core.config import settings
from app.utils.ar_content import build_ar_content_storage_path

router = APIRouter()
logger = structlog.get_logger()

templates = Jinja2Templates(directory="templates")
# Add datetime filter to templates
templates.env.filters["datetime_format"] = datetime_format


def format_bytes(bytes_value: int) -> str:
    """Format bytes to human-readable format."""
    try:
        if bytes_value is None:
            return "0 B"
        bytes_value = int(bytes_value)
        if bytes_value < 0:
            return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"
    except (TypeError, ValueError) as e:
        logger.warning("error_formatting_bytes", value=bytes_value, error=str(e))
        return "0 B"


def calculate_directory_size(directory: Path, max_depth: int = 10) -> Tuple[int, int]:
    """Calculate total size and file count for a directory.
    
    Args:
        directory: Path to the directory
        max_depth: Maximum recursion depth to prevent infinite loops
        
    Returns:
        Tuple of (total_size_bytes, file_count)
    """
    total_size = 0
    file_count = 0
    
    if not directory.exists() or not directory.is_dir():
        return 0, 0
    
    try:
        # Use iterdir() for better performance on large directories
        # Limit depth to prevent performance issues
        def _calculate_recursive(path: Path, depth: int = 0) -> Tuple[int, int]:
            if depth > max_depth:
                return 0, 0
            
            size = 0
            count = 0
            
            try:
                for item in path.iterdir():
                    try:
                        if item.is_file():
                            size += item.stat().st_size
                            count += 1
                        elif item.is_dir():
                            sub_size, sub_count = _calculate_recursive(item, depth + 1)
                            size += sub_size
                            count += sub_count
                    except (OSError, PermissionError):
                        # Skip files/dirs we can't access
                        continue
            except (OSError, PermissionError):
                pass
            
            return size, count
        
        total_size, file_count = _calculate_recursive(directory)
    except (OSError, PermissionError) as e:
        logger.warning("error_calculating_directory_size", 
                      directory=str(directory), 
                      error=str(e))
    
    return total_size, file_count


async def get_storage_info(db: AsyncSession) -> dict:
    """Get real storage information from database and filesystem.
    
    Args:
        db: Database session
        
    Returns:
        Dictionary with storage information
    """
    logger.info("get_storage_info_started")
    try:
        import platform
        import os
        
        # Get disk usage for the storage base path
        storage_base = Path(settings.STORAGE_BASE_PATH)
        if not storage_base.is_absolute():
            storage_base = storage_base.resolve()
        
        # Ensure directory exists
        try:
            storage_base.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning("error_creating_storage_directory", 
                         path=str(storage_base), 
                         error=str(e))
        
        # Get disk usage - cross-platform compatible
        total_disk = 0
        used_disk = 0
        free_disk = 0
        
        try:
            # Get the root path for disk usage calculation
            # Windows: use drive root (e.g., C:\)
            # Linux/Unix: use / (root)
            if platform.system() == "Windows":
                # Get drive letter from path
                drive = storage_base.drive
                if drive:
                    root_path = f"{drive}\\"
                else:
                    root_path = os.getcwd()
            else:
                # Unix/Linux: use root directory
                root_path = "/"
            
            disk_usage = shutil.disk_usage(root_path)
            total_disk = disk_usage.total
            used_disk = disk_usage.used
            free_disk = disk_usage.free
        except Exception as e:
            logger.error("error_getting_disk_usage", 
                    path=str(storage_base),
                    root_path=root_path if 'root_path' in locals() else "unknown",
                    error=str(e),
                    error_type=type(e).__name__)
            total_disk = 0
            used_disk = 0
            free_disk = 0
        
        # Skip AR content size calculation for performance (too slow)
        # Users can check individual company/project storage if needed
        storage_size = 0
        storage_files = 0
        
        # Get companies list (without calculating sizes - too slow)
        try:
            stmt = select(Company).order_by(Company.name)
            result = await db.execute(stmt)
            companies = result.scalars().all()
        except Exception as e:
            logger.error("error_fetching_companies", 
                        error=str(e),
                        traceback=traceback.format_exc())
            companies = []
        
        # Build company list with storage info
        from sqlalchemy import func as sa_func
        from app.core.storage_providers import get_provider_for_company
        from app.core.yandex_disk_provider import YandexDiskStorageProvider

        # Batch load project counts for all companies (avoid N+1)
        company_ids = [c.id for c in companies]
        project_counts_map: dict[int, int] = {}
        if company_ids:
            pc_stmt = (
                select(Project.company_id, sa_func.count(Project.id))
                .where(Project.company_id.in_(company_ids))
                .group_by(Project.company_id)
            )
            pc_result = await db.execute(pc_stmt)
            project_counts_map = {cid: cnt for cid, cnt in pc_result.all()}

        company_storage = []
        yd_quota: dict | None = None  # Filled once for any YD company

        for company in companies:
            try:
                projects_count = project_counts_map.get(company.id, 0)

                storage_type = getattr(company, "storage_provider", "local")
                storage_used = "—"
                storage_used_bytes = 0
                files_count = 0

                if storage_type == "yandex_disk":
                    try:
                        provider = await get_provider_for_company(company)
                        if isinstance(provider, YandexDiskStorageProvider):
                            # Get per-company folder size
                            folder_info = await provider.get_folder_size()
                            storage_used_bytes = folder_info.get("total_bytes", 0)
                            files_count = folder_info.get("file_count", 0)
                            storage_used = format_bytes(storage_used_bytes)

                            # Get overall YD quota once
                            if yd_quota is None:
                                yd_quota = await provider.get_usage_stats()
                    except Exception as exc:
                        logger.warning(
                            "yd_company_usage_failed",
                            company_id=company.id,
                            error=str(exc),
                        )
                else:
                    # Local storage: calculate from filesystem
                    try:
                        company_dir = Path(settings.STORAGE_BASE_PATH) / (getattr(company, "slug", None) or "")
                        if company_dir.exists() and company_dir.is_dir():
                            storage_used_bytes, files_count = calculate_directory_size(company_dir)
                            storage_used = format_bytes(storage_used_bytes)
                    except Exception:
                        pass

                company_storage.append({
                    "id": company.id,
                    "name": getattr(company, "name", "Unknown"),
                    "storage_type": storage_type,
                    "storage_used": storage_used,
                    "storage_used_bytes": storage_used_bytes,
                    "files_count": files_count,
                    "projects_count": projects_count,
                })
            except Exception as e:
                logger.warning(
                    "error_processing_company",
                    company_id=getattr(company, "id", None),
                    error=str(e),
                )
                company_storage.append({
                    "id": getattr(company, "id", 0),
                    "name": getattr(company, "name", "Unknown"),
                    "storage_type": "local",
                    "storage_used": "—",
                    "storage_used_bytes": 0,
                    "files_count": 0,
                    "projects_count": 0,
                })

        result = {
            "total_storage": format_bytes(total_disk) if total_disk > 0 else "Unknown",
            "used_storage": format_bytes(used_disk) if used_disk > 0 else "0 B",
            "available_storage": format_bytes(free_disk) if free_disk > 0 else "Unknown",
            "storage_usage_percent": round((used_disk / total_disk * 100), 2) if total_disk > 0 else 0,
            "ar_content_storage": format_bytes(storage_size),
            "ar_content_files": storage_files,
            "companies": company_storage,
        }

        # Add Yandex Disk quota block if any company uses it
        if yd_quota and yd_quota.get("exists"):
            yd_total = yd_quota.get("total_bytes", 0)
            yd_used = yd_quota.get("used_bytes", 0)
            result["yd_quota"] = {
                "total": format_bytes(yd_total),
                "used": format_bytes(yd_used),
                "free": format_bytes(yd_total - yd_used),
                "percent": round(yd_used / yd_total * 100, 1) if yd_total > 0 else 0,
            }

        return result
    except Exception as e:
        logger.error("error_in_get_storage_info",
                    error=str(e),
                    error_type=type(e).__name__,
                    traceback=traceback.format_exc())
        raise


@router.get("/storage/test")
async def storage_test():
    """Test endpoint to check if storage route is working."""
    import platform
    return {
        "status": "ok", 
        "message": "Storage route is accessible",
        "platform": platform.system()
    }


@router.get("/storage", response_class=HTMLResponse)
async def storage_page(
    request: Request,
    db: AsyncSession = Depends(get_html_db),
    current_user=Depends(get_current_user_optional)
):
    """Storage page with real data."""
    try:
        if not current_user:
            # Redirect to login page if user is not authenticated
            return RedirectResponse(url="/admin/login", status_code=303)
        
        if not current_user.is_active:
            # Redirect to login page if user is not active
            return RedirectResponse(url="/admin/login", status_code=303)
        
        # Get real storage information
        try:
            storage_info = await get_storage_info(db)
        except Exception as e:
            logger.error("error_getting_storage_info", 
                        error=str(e), 
                        error_type=type(e).__name__,
                        traceback=traceback.format_exc())
            # Fallback to empty data on error
            storage_info = {
                "total_storage": "Error",
                "used_storage": "Error",
                "available_storage": "Error",
                "storage_usage_percent": 0,
                "ar_content_storage": "0 B",
                "ar_content_files": 0,
                "providers": [],
                "companies": []
            }
        
        context = {
            "request": request,
            "storage_info": storage_info,
            "current_user": current_user
        }
        return templates.TemplateResponse("storage.html", context)
    except Exception as e:
        logger.error("error_in_storage_page", 
                    error=str(e),
                    error_type=type(e).__name__,
                    traceback=traceback.format_exc())
        # Return error page with fallback data
        error_context = {
            "request": request,
            "storage_info": {
                "total_storage": "Error",
                "used_storage": "Error",
                "available_storage": "Error",
                "storage_usage_percent": 0,
                "ar_content_storage": "0 B",
                "ar_content_files": 0,
                "providers": [],
                "companies": []
            },
            "current_user": current_user if current_user else None,
            "error_message": str(e) if settings.DEBUG else "An error occurred while loading storage information."
        }
        return templates.TemplateResponse("storage.html", error_context, status_code=500)