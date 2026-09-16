"""The migration chain must apply cleanly to an empty database.

This is what CI does on every run, and what a new deployment does on its first
start, so a migration that only works on an already-populated database is a
broken migration even though production never notices.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _upgrade(url: str) -> subprocess.CompletedProcess:
    """Run ``alembic upgrade head`` in a subprocess against *url*.

    A subprocess keeps this off the suite's own engine: ``alembic/env.py`` reads
    ``settings.DATABASE_URL``, and the test env points that at a shared file.
    """
    env = os.environ.copy()
    env["DATABASE_URL"] = url
    return subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.mark.slow
def test_migrations_apply_to_a_fresh_database():
    """``upgrade head`` must succeed on an empty DB, then be a no-op.

    Regression guard: the ``ai_jobs`` migration declared ``index=True`` on the
    ``job_id`` column *and* created ``ix_ai_jobs_job_id`` explicitly. On a fresh
    database the second attempt collided with the first::

        sqlite3.OperationalError: index ix_ai_jobs_job_id already exists

    Production was already at head, so it never re-ran the migration and the
    breakage stayed invisible until a fresh checkout tried to migrate.
    """
    with tempfile.TemporaryDirectory(prefix="arv-migrations-") as tmp:
        url = f"sqlite+aiosqlite:///{Path(tmp).as_posix()}/fresh.db"

        first = _upgrade(url)
        assert first.returncode == 0, (
            "alembic upgrade head failed on an empty database:\n"
            f"{first.stdout}\n{first.stderr}"
        )

        second = _upgrade(url)
        assert second.returncode == 0, (
            "alembic upgrade head is not idempotent:\n"
            f"{second.stdout}\n{second.stderr}"
        )


def test_the_migration_chain_has_exactly_one_head():
    """A branched chain means two conflicting 'latest' revisions."""
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "heads"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    heads = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(heads) == 1, f"expected a single head, got: {heads}"
