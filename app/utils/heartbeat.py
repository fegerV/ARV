"""Dead-man's-switch heartbeat for backup jobs.

Metric-based alerting has a blind spot: if the host is entirely down, the
metrics simply stop arriving and Prometheus sees "no data" rather than "problem".
Pushing a heartbeat to an *external* service after every successful run closes
that gap — the external service alerts when the heartbeat goes missing.

Configure with ``BACKUP_HEARTBEAT_URL`` (e.g. a healthchecks.io ping URL).
Failures are swallowed on purpose: a broken heartbeat must never fail a backup.
"""

from __future__ import annotations

import httpx
import structlog

from app.core.config import get_settings

logger = structlog.get_logger()

_TIMEOUT_SECONDS = 10.0


async def send_heartbeat(status: str = "success", detail: str = "") -> bool:
    """Ping the external dead-man's-switch. Returns True when delivered.

    ``status`` maps to healthchecks.io semantics: ``success`` (default) or
    ``fail``; the latter is sent by appending ``/fail`` to the configured URL.
    """
    settings = get_settings()
    base_url = (settings.BACKUP_HEARTBEAT_URL or "").strip()
    if not base_url:
        return False

    url = base_url.rstrip("/")
    if status == "fail":
        url = f"{url}/fail"

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.post(url, content=detail or status)
        if response.status_code >= 400:
            logger.warning(
                "backup_heartbeat_rejected",
                status_code=response.status_code,
            )
            return False
        return True
    except Exception as exc:  # noqa: BLE001 - never fail a backup over this
        logger.warning("backup_heartbeat_failed", error=str(exc))
        return False
