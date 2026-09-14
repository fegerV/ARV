"""Prometheus metrics for the backup subsystem.

Kept separate from :mod:`app.services.backup_service` so that both the
database and the media backup paths can publish into the same series without
import cycles, and so the collectors are registered exactly once per process.

Alerting rules built on these series are documented in
``docs/BACKUP_AND_RECOVERY.md`` (section "Monitoring").
"""

from __future__ import annotations

import time

import structlog
from prometheus_client import Counter, Gauge

logger = structlog.get_logger()

BACKUP_LAST_SUCCESS = Gauge(
    "arv_backup_last_success_timestamp_seconds",
    "Unix timestamp of the last successful backup, by type and target.",
    ["type", "target"],
)

BACKUP_DURATION = Gauge(
    "arv_backup_duration_seconds",
    "Duration of the last backup run, by type.",
    ["type"],
)

BACKUP_SIZE = Gauge(
    "arv_backup_size_bytes",
    "Size of the last produced backup artifact, by type.",
    ["type"],
)

BACKUP_FAILURES = Counter(
    "arv_backup_failures_total",
    "Total number of failed backup runs, by type and target.",
    ["type", "target"],
)

BACKUP_VERIFY_STATUS = Gauge(
    "arv_backup_verify_status",
    "Result of the last integrity verification (1 = ok, 0 = failed).",
    ["type"],
)

BACKUP_AGE = Gauge(
    "arv_backup_age_seconds",
    "Seconds since the last successful backup, by type.",
    ["type"],
)

BACKUP_RESTORE_DRILL = Gauge(
    "arv_backup_restore_drill_last_timestamp_seconds",
    "Unix timestamp of the last successful restore drill.",
)


def record_success(backup_type: str, target: str, size_bytes: int | None, duration_s: float) -> None:
    """Publish a successful run to the metric series."""
    now = time.time()
    BACKUP_LAST_SUCCESS.labels(type=backup_type, target=target or "unknown").set(now)
    BACKUP_DURATION.labels(type=backup_type).set(duration_s)
    BACKUP_AGE.labels(type=backup_type).set(0)
    if size_bytes is not None:
        BACKUP_SIZE.labels(type=backup_type).set(size_bytes)


def record_failure(backup_type: str, target: str = "") -> None:
    """Publish a failed run to the metric series."""
    BACKUP_FAILURES.labels(type=backup_type, target=target or "unknown").inc()


def record_verification(backup_type: str, ok: bool) -> None:
    """Publish the outcome of an integrity verification."""
    BACKUP_VERIFY_STATUS.labels(type=backup_type).set(1 if ok else 0)


def record_restore_drill(ok: bool) -> None:
    """Publish the outcome of a restore drill."""
    if ok:
        BACKUP_RESTORE_DRILL.set(time.time())
