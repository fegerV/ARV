"""
Yandex Disk storage provider for Vertex AR platform.

Implements the StorageProvider interface using the Yandex Disk REST API
(https://yandex.ru/dev/disk-api/doc/ru/).
Files are stored under ``app:/{base_prefix}/…`` in the application folder.
"""

from __future__ import annotations

import io
import tempfile
from pathlib import PurePosixPath
from typing import Any, Dict, Optional

import httpx
import structlog

from app.core.storage_providers import StorageProvider

logger = structlog.get_logger()

_DISK_API = "https://cloud-api.yandex.net/v1/disk"
_DEFAULT_TIMEOUT = 30.0
_UPLOAD_TIMEOUT = 120.0


class YandexDiskStorageProvider(StorageProvider):
    """Storage provider backed by Yandex Disk REST API."""

    def __init__(self, oauth_token: str, base_prefix: str = "VertexAR") -> None:
        """
        Initialise provider.

        Args:
            oauth_token: Yandex OAuth bearer token.
            base_prefix: Root folder name inside the app folder on Disk.
        """
        self._token = oauth_token
        self._base_prefix = base_prefix
        self._headers = {"Authorization": f"OAuth {self._token}"}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _disk_path(self, relative_path: str) -> str:
        """Build ``app:/prefix/relative`` path for the Disk API."""
        relative_path = relative_path.replace("\\", "/").lstrip("/")
        return f"app:/{self._base_prefix}/{relative_path}"

    async def _ensure_directory(self, disk_path: str) -> None:
        """Recursively create directories on Disk (mkdir -p equivalent)."""
        parts = PurePosixPath(disk_path).parts
        # ``parts`` for ``app:/VertexAR/slug/001`` → ('app:', 'VertexAR', 'slug', '001')
        # Начинаем с i=2, т.к. "app:" — корень YD, его нельзя создать через mkdir
        for i in range(2, len(parts) + 1):
            folder = "/".join(parts[:i])
            async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
                resp = await client.put(
                    f"{_DISK_API}/resources",
                    params={"path": folder},
                    headers=self._headers,
                )
                # 201 — created, 409 — already exists
                if resp.status_code not in (201, 409):
                    logger.warning(
                        "yd_mkdir_unexpected_status",
                        path=folder,
                        status=resp.status_code,
                        body=resp.text[:300],
                    )

    # ------------------------------------------------------------------
    # StorageProvider interface
    # ------------------------------------------------------------------

    async def save_file(self, source_path: str, destination_path: str) -> str:
        """Upload a local file to Yandex Disk."""
        disk_path = self._disk_path(destination_path)
        parent = str(PurePosixPath(disk_path).parent)
        await self._ensure_directory(parent)

        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            # Step 1: get upload URL
            resp = await client.get(
                f"{_DISK_API}/resources/upload",
                params={"path": disk_path, "overwrite": "true"},
                headers=self._headers,
            )
            resp.raise_for_status()
            upload_url = resp.json()["href"]

            # Step 2: PUT the file
            with open(source_path, "rb") as fh:
                data = fh.read()
            upload_resp = await client.put(
                upload_url,
                content=data,
                headers={"Content-Type": "application/octet-stream"},
                timeout=_UPLOAD_TIMEOUT,
            )
            upload_resp.raise_for_status()

        logger.info("yd_file_uploaded", disk_path=disk_path)
        # Return an internal reference; resolved at serve-time.
        return f"yadisk://{destination_path.replace(chr(92), '/').lstrip('/')}"

    async def save_file_bytes(self, content: bytes, destination_path: str) -> str:
        """Upload raw bytes (QR code, thumbnail, etc.) to Yandex Disk."""
        disk_path = self._disk_path(destination_path)
        parent = str(PurePosixPath(disk_path).parent)
        await self._ensure_directory(parent)

        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            resp = await client.get(
                f"{_DISK_API}/resources/upload",
                params={"path": disk_path, "overwrite": "true"},
                headers=self._headers,
            )
            resp.raise_for_status()
            upload_url = resp.json()["href"]

            upload_resp = await client.put(
                upload_url,
                content=content,
                headers={"Content-Type": "application/octet-stream"},
                timeout=_UPLOAD_TIMEOUT,
            )
            upload_resp.raise_for_status()

        logger.info("yd_bytes_uploaded", disk_path=disk_path)
        return f"yadisk://{destination_path.replace(chr(92), '/').lstrip('/')}"

    async def get_file(self, storage_path: str, local_path: str) -> bool:
        """Download a file from Yandex Disk to a local path."""
        disk_path = self._disk_path(storage_path)
        try:
            async with httpx.AsyncClient(timeout=_UPLOAD_TIMEOUT) as client:
                resp = await client.get(
                    f"{_DISK_API}/resources/download",
                    params={"path": disk_path},
                    headers=self._headers,
                )
                resp.raise_for_status()
                download_url = resp.json()["href"]

                dl_resp = await client.get(download_url, follow_redirects=True)
                dl_resp.raise_for_status()

                import aiofiles
                async with aiofiles.open(local_path, "wb") as fh:
                    await fh.write(dl_resp.content)

            logger.info("yd_file_downloaded", disk_path=disk_path, local_path=local_path)
            return True
        except Exception as exc:
            logger.error("yd_file_download_failed", disk_path=disk_path, error=str(exc))
            return False

    async def delete_file(self, storage_path: str) -> bool:
        """Delete a file or folder from Yandex Disk."""
        disk_path = self._disk_path(storage_path)
        try:
            async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
                resp = await client.delete(
                    f"{_DISK_API}/resources",
                    params={"path": disk_path, "permanently": "true"},
                    headers=self._headers,
                )
                if resp.status_code in (202, 204):
                    logger.info("yd_file_deleted", disk_path=disk_path)
                    return True
                if resp.status_code == 404:
                    return False
                resp.raise_for_status()
                return True
        except Exception as exc:
            logger.error("yd_file_delete_failed", disk_path=disk_path, error=str(exc))
            return False

    async def file_exists(self, storage_path: str) -> bool:
        """Check whether a resource exists on Yandex Disk."""
        disk_path = self._disk_path(storage_path)
        try:
            async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
                resp = await client.get(
                    f"{_DISK_API}/resources",
                    params={"path": disk_path},
                    headers=self._headers,
                )
                return resp.status_code == 200
        except Exception:
            return False

    def get_public_url(self, storage_path: str) -> str:
        """Return internal ``yadisk://`` reference (resolved at serve-time)."""
        storage_path = storage_path.replace("\\", "/").lstrip("/")
        return f"yadisk://{storage_path}"

    async def get_download_url(self, storage_path: str) -> Optional[str]:
        """
        Obtain a temporary direct-download URL from Yandex Disk.

        The link is valid for ~30 minutes — long enough for an AR session.
        """
        disk_path = self._disk_path(storage_path)
        try:
            async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
                resp = await client.get(
                    f"{_DISK_API}/resources/download",
                    params={"path": disk_path},
                    headers=self._headers,
                )
                resp.raise_for_status()
                return resp.json()["href"]
        except Exception as exc:
            logger.error("yd_download_url_failed", disk_path=disk_path, error=str(exc))
            return None

    async def get_folder_size(self, relative_path: str = "") -> Dict[str, Any]:
        """Calculate total size and file count for a folder on Yandex Disk.

        Recursively traverses the folder tree via the Disk REST API and
        sums up file sizes.

        Args:
            relative_path: Path relative to base_prefix (empty = root folder).

        Returns:
            ``{"total_bytes": int, "file_count": int}``
        """
        disk_path = self._disk_path(relative_path) if relative_path else f"app:/{self._base_prefix}"

        async def _sum_dir(dir_path: str, client: httpx.AsyncClient, depth: int = 0) -> tuple[int, int]:
            """Return (total_bytes, file_count) for *dir_path*."""
            if depth > 10:
                return 0, 0
            total = 0
            count = 0
            offset = 0
            limit = 100
            while True:
                try:
                    resp = await client.get(
                        f"{_DISK_API}/resources",
                        params={
                            "path": dir_path,
                            "limit": limit,
                            "offset": offset,
                            "fields": "_embedded.items.type,_embedded.items.size,_embedded.items.path,_embedded.total",
                        },
                        headers=self._headers,
                    )
                    if resp.status_code != 200:
                        break
                    embedded = resp.json().get("_embedded", {})
                    items = embedded.get("items", [])
                    for item in items:
                        if item.get("type") == "file":
                            total += item.get("size", 0)
                            count += 1
                        elif item.get("type") == "dir":
                            sub_total, sub_count = await _sum_dir(item["path"], client, depth + 1)
                            total += sub_total
                            count += sub_count
                    items_total = embedded.get("total", 0)
                    offset += limit
                    if offset >= items_total:
                        break
                except Exception:
                    break
            return total, count

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                total_bytes, file_count = await _sum_dir(disk_path, client)
            return {"total_bytes": total_bytes, "file_count": file_count}
        except Exception as exc:
            logger.error("yd_folder_size_failed", path=disk_path, error=str(exc))
            return {"total_bytes": 0, "file_count": 0, "error": str(exc)}

    async def get_usage_stats(self, path: str = "") -> Dict[str, Any]:
        """Return Yandex Disk quota information."""
        try:
            async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
                resp = await client.get(
                    _DISK_API,
                    headers=self._headers,
                )
                resp.raise_for_status()
                data = resp.json()
                total = data.get("total_space", 0)
                used = data.get("used_space", 0)
                return {
                    "total_bytes": total,
                    "used_bytes": used,
                    "free_bytes": total - used,
                    "total_mb": round(total / (1024 * 1024), 2),
                    "used_mb": round(used / (1024 * 1024), 2),
                    "provider": "yandex_disk",
                    "exists": True,
                }
        except Exception as exc:
            logger.error("yd_usage_stats_failed", error=str(exc))
            return {
                "total_bytes": 0,
                "used_bytes": 0,
                "free_bytes": 0,
                "provider": "yandex_disk",
                "exists": False,
                "error": str(exc),
            }
