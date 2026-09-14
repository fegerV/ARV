"""Tests for the GFS retention ladder (``app/services/backup_rotation.py``).

The rule exists to fix a specific, observable defect: with "keep the N newest
copies" a restore point from a month ago has already been evicted by the time
damage is noticed. The tests below pin that property directly.
"""

from datetime import date, datetime, timedelta

from app.services.backup_rotation import (
    gfs_period_keys,
    select_gfs_deletes,
    select_gfs_keeps,
)


def _daily_series(now: datetime, days: int) -> list[datetime]:
    """One backup per day at 03:00, newest first."""
    return [now - timedelta(days=offset) for offset in range(days)]


def test_keeps_only_the_newest_per_period_when_only_daily_is_enabled():
    now = datetime(2026, 9, 14, 3, 0, 0)
    backups = _daily_series(now, 10)

    keeps = select_gfs_keeps(
        backups, keep_daily=3, keep_weekly=0, keep_monthly=0, keep_yearly=0
    )

    assert keeps == backups[:3]


def test_disabled_tiers_keep_nothing():
    now = datetime(2026, 9, 14, 3, 0, 0)
    backups = _daily_series(now, 5)

    keeps = select_gfs_keeps(
        backups, keep_daily=0, keep_weekly=0, keep_monthly=0, keep_yearly=0
    )

    assert keeps == []


def test_empty_input_returns_empty():
    assert select_gfs_keeps([]) == []


def test_unsorted_input_is_normalised_to_newest_first():
    now = datetime(2026, 9, 14, 3, 0, 0)
    backups = list(reversed(_daily_series(now, 6)))

    keeps = select_gfs_keeps(
        backups, keep_daily=2, keep_weekly=0, keep_monthly=0, keep_yearly=0
    )

    assert keeps == [now, now - timedelta(days=1)]


def test_monthly_tier_retains_a_point_the_legacy_rule_had_evicted():
    """The core regression: GFS keeps what "30 newest copies" already dropped."""
    now = datetime(2026, 9, 14, 3, 0, 0)
    backups = _daily_series(now, 60)

    legacy_keeps = backups[:30]
    keeps = select_gfs_keeps(backups)

    month_ago = now - timedelta(days=45)
    assert month_ago not in legacy_keeps, "precondition: legacy rule evicted it"
    assert month_ago in keeps, "GFS must still hold a ~6-week-old restore point"


def test_default_ladder_is_bounded_by_the_sum_of_its_tiers():
    now = datetime(2026, 9, 14, 3, 0, 0)
    backups = _daily_series(now, 400)

    keeps = select_gfs_keeps(backups)

    # 7 daily + 4 weekly + 12 monthly + 3 yearly, less the overlap between tiers.
    assert len(keeps) <= 26
    assert len(keeps) >= 7
    assert now in keeps


def test_yearly_tier_reaches_beyond_a_year():
    """Only the yearly tier can reach back to a previous calendar year."""
    now = datetime(2026, 9, 14, 3, 0, 0)
    backups = _daily_series(now, 1300)  # ~3.5 years of dailies
    # Newest artifact of calendar year 2024.
    previous_years_point = datetime(2024, 12, 31, 3, 0, 0)

    with_yearly = select_gfs_keeps(backups)
    without_yearly = select_gfs_keeps(backups, keep_yearly=0)

    assert previous_years_point in with_yearly
    assert previous_years_point not in without_yearly, (
        "daily/weekly/monthly tiers must not reach back that far"
    )


def test_deletes_are_the_exact_complement_of_keeps():
    now = datetime(2026, 9, 14, 3, 0, 0)
    backups = _daily_series(now, 90)

    keeps = select_gfs_keeps(backups)
    deletes = select_gfs_deletes(backups)

    assert set(keeps).isdisjoint(deletes)
    assert sorted(keeps + deletes, reverse=True) == sorted(backups, reverse=True)


def test_rows_with_started_at_are_supported():
    """The service passes ORM rows, not bare datetimes."""

    class Row:
        def __init__(self, started_at):
            self.started_at = started_at

    now = datetime(2026, 9, 14, 3, 0, 0)
    rows = [Row(now - timedelta(days=offset)) for offset in range(5)]

    keeps = select_gfs_keeps(
        rows, keep_daily=2, keep_weekly=0, keep_monthly=0, keep_yearly=0
    )

    assert keeps == rows[:2]


def test_gfs_period_keys_reports_each_tier():
    keys = gfs_period_keys(datetime(2026, 9, 14, 3, 0, 0))
    day_key, week_key, month_key, year_key = keys

    assert day_key == date(2026, 9, 14)
    assert week_key[0] == 2026
    assert month_key == (2026, 9)
    assert year_key == 2026
