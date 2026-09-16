"""Tests for the cross-process guard around the scheduled database backup.

The bug these exist for: gunicorn runs several workers, each starts its own
APScheduler during lifespan, and the cron job therefore fired once per worker
in the same second. Both runs computed the same artifact name, uploaded to the
same remote key, and wrote separate ``backup_history`` rows pointing at that
one artifact. Rotation then deleted the older row and the file with it,
leaving the surviving row marked ``success`` while its artifact was gone.

Observed in production on 2026-09-16 (backup 150, 404 from Yandex Disk).
"""

import os

import pytest
import structlog

from app.core import scheduler as scheduler_mod


def test_lock_path_is_the_one_the_shell_script_uses():
    """The in-app scheduler and backup-db.sh must contend on the same file.

    If they used different locks, enabling arv-backup-db.timer alongside the
    in-app scheduler would run two dumps — the exact situation the shared lock
    is there to prevent.
    """
    # deploy/backup/backup-db.sh calls `acquire_lock "db"`, and common.sh
    # builds "${LOCK_DIR}/arv-${name}.lock" with LOCK_DIR defaulting to
    # /var/lock. Assert the whole path, not just the basename: a different
    # directory would break the exclusion just as thoroughly.
    assert scheduler_mod._resolve_lock_path({}) == "/var/lock/arv-db.lock"


@pytest.mark.asyncio
async def test_job_skips_when_another_process_holds_the_lock(monkeypatch):
    """The loser of the race must do nothing at all."""
    ran: list[bool] = []

    class _HeldLock:
        def __init__(self, _path):
            pass

        def acquire(self):
            return False

        def release(self):  # pragma: no cover - must not be needed
            raise AssertionError("release() called on a lock we never took")

    async def _fake_run():
        ran.append(True)

    monkeypatch.setattr(scheduler_mod, "JobLock", _HeldLock)
    monkeypatch.setattr(scheduler_mod, "_run_scheduled_backup", _fake_run)

    await scheduler_mod._scheduled_backup_job()

    assert ran == []


@pytest.mark.asyncio
async def test_job_runs_and_releases_the_lock(monkeypatch):
    events: list[str] = []

    class _FreeLock:
        def __init__(self, path):
            self.path = path

        def acquire(self):
            events.append("acquire")
            return True

        def release(self):
            events.append("release")

    async def _fake_run():
        events.append("run")

    monkeypatch.setattr(scheduler_mod, "JobLock", _FreeLock)
    monkeypatch.setattr(scheduler_mod, "_run_scheduled_backup", _fake_run)

    await scheduler_mod._scheduled_backup_job()

    assert events == ["acquire", "run", "release"]


@pytest.mark.asyncio
async def test_lock_is_released_even_when_the_backup_explodes(monkeypatch):
    """A crash mid-run must not wedge the job forever."""
    events: list[str] = []

    class _FreeLock:
        def __init__(self, _path):
            pass

        def acquire(self):
            return True

        def release(self):
            events.append("release")

    async def _boom():
        raise RuntimeError("pg_dump vanished")

    monkeypatch.setattr(scheduler_mod, "JobLock", _FreeLock)
    monkeypatch.setattr(scheduler_mod, "_run_scheduled_backup", _boom)

    with pytest.raises(RuntimeError):
        await scheduler_mod._scheduled_backup_job()

    assert events == ["release"]


@pytest.mark.skipif(
    scheduler_mod.fcntl is None, reason="flock is POSIX-only; production is Linux"
)
def test_lock_is_actually_exclusive(tmp_path):
    """The real primitive, not a stand-in: two holders cannot coexist."""
    path = str(tmp_path / "arv-db.lock")

    first = scheduler_mod.JobLock(path)
    second = scheduler_mod.JobLock(path)

    assert first.acquire() is True
    assert second.acquire() is False

    first.release()
    # Once released, the next runner may proceed.
    assert second.acquire() is True
    second.release()


@pytest.mark.skipif(
    scheduler_mod.fcntl is None, reason="flock is POSIX-only; production is Linux"
)
def test_lock_creates_its_parent_directory(tmp_path):
    """The lock lives in /var/lock, which may not exist on a fresh host."""
    path = str(tmp_path / "nested" / "arv-db.lock")

    lock = scheduler_mod.JobLock(path)
    try:
        assert lock.acquire() is True
        assert os.path.exists(path)
    finally:
        lock.release()


@pytest.mark.skipif(
    scheduler_mod.fcntl is None, reason="flock is POSIX-only; production is Linux"
)
def test_unusable_lock_file_lets_the_backup_run(tmp_path):
    """A broken lock must not silently stop backups.

    Skipping is the right answer for contention and the wrong answer for a
    lock we cannot create at all: the job would then never run again, and the
    failure would be invisible because nothing raises.
    """
    # A directory where the lock file should be: open() cannot succeed.
    path = str(tmp_path / "arv-db.lock")
    os.mkdir(path)

    lock = scheduler_mod.JobLock(path)

    with structlog.testing.capture_logs() as captured:
        assert lock.acquire() is True
    lock.release()

    # Running on is only acceptable if it is *loud*: the operator needs to be
    # able to find out that the guard is not working.
    assert any(e["event"] == "backup_lock_unavailable" for e in captured)


def test_lock_dir_env_var_is_honoured():
    """ARV_BACKUP_LOCK_DIR must move the scheduler with the shell scripts.

    common.sh builds "${LOCK_DIR}/arv-${name}.lock" from this variable. If the
    scheduler ignored it, relocating the lock directory would leave the two
    locking different files — mutual exclusion gone, no error raised.
    """
    assert (
        scheduler_mod._resolve_lock_path({"ARV_BACKUP_LOCK_DIR": "/run/mylock"})
        == os.path.join("/run/mylock", "arv-db.lock")
    )


def test_explicit_lock_path_wins():
    assert (
        scheduler_mod._resolve_lock_path(
            {
                "ARV_BACKUP_LOCK_PATH": "/tmp/pinned.lock",
                "ARV_BACKUP_LOCK_DIR": "/run/mylock",
            }
        )
        == "/tmp/pinned.lock"
    )
