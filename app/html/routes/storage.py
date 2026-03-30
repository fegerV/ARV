import asyncio
import copy
import shutil
import structlog
import time
import traceback
from pathlib import Path
from typing import Tuple

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_current_user_optional
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.html.deps import get_html_db
from app.html.templating import templates
from app.html.utils import require_active_user
from app.models.company import Company
from app.models.project import Project

router = APIRouter()
logger = structlog.get_logger()

_STORAGE_INFO_CACHE_TTL = 60.0
_STORAGE_INFO_BUILD_TIMEOUT = 4.0
_STORAGE_INFO_PROVIDER_TIMEOUT = 2.5
_STORAGE_INFO_LOCAL_SIZE_TIMEOUT = 1.5
_STORAGE_INFO_PROVIDER_CONCURRENCY = 3
_STORAGE_INFO_CACHE: dict[str, object] = {
    "value": None,
    "timestamp": 0.0,
    "refresh_task": None,
}


def format_bytes(bytes_value: int) -> str:
    """Format bytes to human-readable format."""
    try:
        if bytes_value is None:
            return "0 B"
        bytes_value = int(bytes_value)
        if bytes_value < 0:
            return "0 B"
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"
    except (TypeError, ValueError) as e:
        logger.warning("error_formatting_bytes", value=bytes_value, error=str(e))
        return "0 B"


def calculate_directory_size(directory: Path, max_depth: int = 10) -> Tuple[int, int]:
    """Calculate total size and file count for a directory."""
    total_size = 0
    file_count = 0

    if not directory.exists() or not directory.is_dir():
        return 0, 0

    try:
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
                        continue
            except (OSError, PermissionError):
                pass

            return size, count

        total_size, file_count = _calculate_recursive(directory)
    except (OSError, PermissionError) as e:
        logger.warning("error_calculating_directory_size", directory=str(directory), error=str(e))

    return total_size, file_count


def _default_storage_info() -> dict:
    """Fallback storage payload for error paths."""
    return {
        "total_storage": "Error",
        "used_storage": "Error",
        "available_storage": "Error",
        "storage_usage_percent": 0,
        "ar_content_storage": "0 B",
        "ar_content_files": 0,
        "providers": [],
        "companies": [],
    }


async def _build_storage_info(db: AsyncSession) -> dict:
    """Collect real storage information from database and providers."""
    logger.info("get_storage_info_started")
    try:
        import os
        import platform
        from sqlalchemy import func as sa_func

        from app.core.storage_providers import get_provider_for_company
        from app.core.yandex_disk_provider import YandexDiskStorageProvider

        storage_base = Path(settings.STORAGE_BASE_PATH)
        if not storage_base.is_absolute():
            storage_base = storage_base.resolve()

        try:
            storage_base.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning("error_creating_storage_directory", path=str(storage_base), error=str(e))

        total_disk = 0
        used_disk = 0
        free_disk = 0

        try:
            if platform.system() == "Windows":
                drive = storage_base.drive
                root_path = f"{drive}\\" if drive else os.getcwd()
            else:
                root_path = "/"

            disk_usage = shutil.disk_usage(root_path)
            total_disk = disk_usage.total
            used_disk = disk_usage.used
            free_disk = disk_usage.free
        except Exception as e:
            logger.error(
                "error_getting_disk_usage",
                path=str(storage_base),
                root_path=root_path if "root_path" in locals() else "unknown",
                error=str(e),
                error_type=type(e).__name__,
            )

        storage_size = 0
        storage_files = 0

        try:
            stmt = select(Company).order_by(Company.name)
            result = await db.execute(stmt)
            companies = result.scalars().all()
        except Exception as e:
            logger.error("error_fetching_companies", error=str(e), traceback=traceback.format_exc())
            companies = []

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

        quota_state: dict[str, object] = {"value": None}
        quota_lock = asyncio.Lock()
        provider_semaphore = asyncio.Semaphore(_STORAGE_INFO_PROVIDER_CONCURRENCY)

        async def _build_company_storage(company: Company) -> dict:
            try:
                projects_count = project_counts_map.get(company.id, 0)
                storage_type = getattr(company, "storage_provider", "local")
                storage_used = "—"
                storage_used_bytes = 0
                files_count = 0

                if storage_type == "yandex_disk":
                    try:
                        async with provider_semaphore:
                            provider = await asyncio.wait_for(
                                get_provider_for_company(company),
                                timeout=_STORAGE_INFO_PROVIDER_TIMEOUT,
                            )
                            if isinstance(provider, YandexDiskStorageProvider):
                                folder_info = await asyncio.wait_for(
                                    provider.get_folder_size(),
                                    timeout=_STORAGE_INFO_PROVIDER_TIMEOUT,
                                )
                                storage_used_bytes = folder_info.get("total_bytes", 0)
                                files_count = folder_info.get("file_count", 0)
                                storage_used = format_bytes(storage_used_bytes)

                                if quota_state["value"] is None:
                                    async with quota_lock:
                                        if quota_state["value"] is None:
                                            quota_state["value"] = await asyncio.wait_for(
                                                provider.get_usage_stats(),
                                                timeout=_STORAGE_INFO_PROVIDER_TIMEOUT,
                                            )
                    except Exception as exc:
                        logger.warning("yd_company_usage_failed", company_id=company.id, error=str(exc))
                else:
                    try:
                        company_dir = Path(settings.STORAGE_BASE_PATH) / (getattr(company, "slug", None) or "")
                        if company_dir.exists() and company_dir.is_dir():
                            storage_used_bytes, files_count = await asyncio.wait_for(
                                asyncio.to_thread(calculate_directory_size, company_dir),
                                timeout=_STORAGE_INFO_LOCAL_SIZE_TIMEOUT,
                            )
                            storage_used = format_bytes(storage_used_bytes)
                    except Exception as exc:
                        logger.warning("local_company_usage_failed", company_id=company.id, error=str(exc))

                return {
                    "id": company.id,
                    "name": getattr(company, "name", "Unknown"),
                    "storage_type": storage_type,
                    "storage_used": storage_used,
                    "storage_used_bytes": storage_used_bytes,
                    "files_count": files_count,
                    "projects_count": projects_count,
                }
            except Exception as e:
                logger.warning("error_processing_company", company_id=getattr(company, "id", None), error=str(e))
                return {
                    "id": getattr(company, "id", 0),
                    "name": getattr(company, "name", "Unknown"),
                    "storage_type": getattr(company, "storage_provider", "local"),
                    "storage_used": "—",
                    "storage_used_bytes": 0,
                    "files_count": 0,
                    "projects_count": project_counts_map.get(getattr(company, "id", 0), 0),
                }

        company_storage = []
        if companies:
            company_storage = await asyncio.gather(*(_build_company_storage(company) for company in companies))

        result = {
            "total_storage": format_bytes(total_disk) if total_disk > 0 else "Unknown",
            "used_storage": format_bytes(used_disk) if used_disk > 0 else "0 B",
            "available_storage": format_bytes(free_disk) if free_disk > 0 else "Unknown",
            "storage_usage_percent": round((used_disk / total_disk * 100), 2) if total_disk > 0 else 0,
            "ar_content_storage": format_bytes(storage_size),
            "ar_content_files": storage_files,
            "companies": company_storage,
        }

        yd_quota = quota_state["value"]
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
        logger.error(
            "error_in_get_storage_info",
            error=str(e),
            error_type=type(e).__name__,
            traceback=traceback.format_exc(),
        )
        raise


def _storage_info_cache_is_fresh(now: float | None = None) -> bool:
    """Return whether the in-memory storage info cache is still fresh."""
    now = time.monotonic() if now is None else now
    cached_value = _STORAGE_INFO_CACHE.get("value")
    cached_at = _STORAGE_INFO_CACHE.get("timestamp", 0.0)
    return cached_value is not None and (now - float(cached_at)) < _STORAGE_INFO_CACHE_TTL


def _storage_info_cache_has_value() -> bool:
    """Return whether the in-memory cache has any value, even stale."""
    return _STORAGE_INFO_CACHE.get("value") is not None


async def _refresh_storage_info_cache() -> None:
    """Refresh storage info using an isolated background DB session."""
    try:
        async with AsyncSessionLocal() as db:
            storage_info = await asyncio.wait_for(
                _build_storage_info(db),
                timeout=_STORAGE_INFO_BUILD_TIMEOUT,
            )
        _STORAGE_INFO_CACHE["value"] = copy.deepcopy(storage_info)
        _STORAGE_INFO_CACHE["timestamp"] = time.monotonic()
        logger.info("get_storage_info_cache_refresh")
    except Exception as exc:
        logger.warning("get_storage_info_cache_refresh_failed", error=str(exc))
    finally:
        _STORAGE_INFO_CACHE["refresh_task"] = None


def _schedule_storage_info_refresh() -> None:
    """Refresh storage info in the background if no refresh is already running."""
    existing_task = _STORAGE_INFO_CACHE.get("refresh_task")
    if existing_task and not existing_task.done():
        return
    try:
        _STORAGE_INFO_CACHE["refresh_task"] = asyncio.create_task(_refresh_storage_info_cache())
        logger.info("get_storage_info_cache_refresh_scheduled")
    except RuntimeError:
        logger.warning("get_storage_info_cache_refresh_schedule_failed")


async def get_storage_info(db: AsyncSession) -> dict:
    """Get storage information, reusing a short-lived cache for the admin page."""
    now = time.monotonic()
    if _storage_info_cache_is_fresh(now):
        logger.info("get_storage_info_cache_hit")
        return copy.deepcopy(_STORAGE_INFO_CACHE["value"])

    if _storage_info_cache_has_value():
        _schedule_storage_info_refresh()
        logger.info("get_storage_info_cache_stale_hit")
        return copy.deepcopy(_STORAGE_INFO_CACHE["value"])

    storage_info = await asyncio.wait_for(_build_storage_info(db), timeout=_STORAGE_INFO_BUILD_TIMEOUT)
    _STORAGE_INFO_CACHE["value"] = copy.deepcopy(storage_info)
    _STORAGE_INFO_CACHE["timestamp"] = now
    logger.info("get_storage_info_cache_refresh")
    return storage_info


@router.get("/storage/test")
async def storage_test():
    """Test endpoint to check if storage route is working."""
    import platform

    return {
        "status": "ok",
        "message": "Storage route is accessible",
        "platform": platform.system(),
    }


@router.get("/storage", response_class=HTMLResponse)
async def storage_page(
    request: Request,
    db: AsyncSession = Depends(get_html_db),
    current_user=Depends(get_current_user_optional),
):
    """Storage page with real data."""
    try:
        redirect = require_active_user(current_user)
        if redirect:
            return redirect

        try:
            storage_info = await get_storage_info(db)
        except Exception as e:
            logger.error(
                "error_getting_storage_info",
                error=str(e),
                error_type=type(e).__name__,
                traceback=traceback.format_exc(),
            )
            storage_info = _default_storage_info()

        context = {
            "request": request,
            "storage_info": storage_info,
            "current_user": current_user,
        }
        return templates.TemplateResponse("storage.html", context)
    except Exception as e:
        logger.error(
            "error_in_storage_page",
            error=str(e),
            error_type=type(e).__name__,
            traceback=traceback.format_exc(),
        )
        error_context = {
            "request": request,
            "storage_info": _default_storage_info(),
            "current_user": current_user if current_user else None,
            "error_message": str(e) if settings.DEBUG else "An error occurred while loading storage information.",
        }
        return templates.TemplateResponse("storage.html", error_context, status_code=500)
