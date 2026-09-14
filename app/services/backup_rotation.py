"""Grandfather-father-son (GFS) retention selection.

The previous retention rule (``max_copies`` newest + ``retention_days``) could
not answer "restore the state from a month ago" — every long-lived point had
already been evicted. GFS keeps a few recent points at high resolution and a
few older points at low resolution, which is what a real incident needs
(damage is often noticed weeks after it happens).

The selection mirrors ``restic forget --keep-daily/-weekly/-monthly/-yearly``:
for each tier we keep the *newest* artifact in each of the newest N distinct
periods.

Pure functions only — no database or filesystem access — so the rule can be
unit-tested directly.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Callable, Iterable, Sequence, TypeVar

T = TypeVar("T")

# Default ladder from docs/BACKUP_AND_RECOVERY.md (~26 restore points).
DEFAULT_KEEP_DAILY = 7
DEFAULT_KEEP_WEEKLY = 4
DEFAULT_KEEP_MONTHLY = 12
DEFAULT_KEEP_YEARLY = 3


def _as_datetime(value: object) -> datetime:
    """Extract a datetime from a BackupHistory-like object or the value itself."""
    if isinstance(value, datetime):
        return value
    for attr in ("started_at", "finished_at"):
        candidate = getattr(value, attr, None)
        if isinstance(candidate, datetime):
            return candidate
    raise TypeError(f"Cannot determine timestamp for {value!r}")


def _newest_per_period(
    items_newest_first: Sequence[T],
    period_key: Callable[[T], object],
    count: int,
) -> list[T]:
    """Return the newest item in each of the newest *count* distinct periods."""
    if count <= 0:
        return []
    seen: set[object] = set()
    kept: list[T] = []
    for item in items_newest_first:
        key = period_key(item)
        if key in seen:
            continue
        seen.add(key)
        kept.append(item)
        if len(kept) >= count:
            break
    return kept


def select_gfs_keeps(
    backups: Iterable[T],
    keep_daily: int = DEFAULT_KEEP_DAILY,
    keep_weekly: int = DEFAULT_KEEP_WEEKLY,
    keep_monthly: int = DEFAULT_KEEP_MONTHLY,
    keep_yearly: int = DEFAULT_KEEP_YEARLY,
) -> list[T]:
    """Return the subset of *backups* that must be retained.

    *backups* may be ``BackupHistory`` rows or plain datetimes. The result is
    ordered newest-first.
    """
    ordered = sorted(backups, key=_as_datetime, reverse=True)
    if not ordered:
        return []

    def _day(item: T) -> object:
        return _as_datetime(item).date()

    def _week(item: T) -> object:
        iso = _as_datetime(item).isocalendar()
        return (iso[0], iso[1])

    def _month(item: T) -> object:
        dt = _as_datetime(item)
        return (dt.year, dt.month)

    def _year(item: T) -> object:
        return _as_datetime(item).year

    keep: dict[int, T] = {}
    for keyfunc, count in (
        (_day, keep_daily),
        (_week, keep_weekly),
        (_month, keep_monthly),
        (_year, keep_yearly),
    ):
        for item in _newest_per_period(ordered, keyfunc, count):
            keep[id(item)] = item

    return [item for item in ordered if id(item) in keep]


def select_gfs_deletes(
    backups: Iterable[T],
    keep_daily: int = DEFAULT_KEEP_DAILY,
    keep_weekly: int = DEFAULT_KEEP_WEEKLY,
    keep_monthly: int = DEFAULT_KEEP_MONTHLY,
    keep_yearly: int = DEFAULT_KEEP_YEARLY,
) -> list[T]:
    """Return the subset of *backups* that exceeds the GFS ladder."""
    items = list(backups)
    keep_ids = {id(item) for item in select_gfs_keeps(
        items,
        keep_daily=keep_daily,
        keep_weekly=keep_weekly,
        keep_monthly=keep_monthly,
        keep_yearly=keep_yearly,
    )}
    return [item for item in items if id(item) not in keep_ids]


def gfs_period_keys(when: datetime) -> tuple[date, tuple[int, int], tuple[int, int], int]:
    """Return the (day, iso-week, month, year) keys used by the ladder.

    Exposed mainly so tests can reason about the ladder without re-deriving it.
    """
    iso = when.isocalendar()
    return (when.date(), (iso[0], iso[1]), (when.year, when.month), when.year)
