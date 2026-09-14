"""Thin async wrapper around external command execution for backup tooling.

Every backup component (``pg_dump``, ``age``, ``rclone``, ``restic``,
``pg_restore``) shells out to a host binary. Centralising the subprocess call
means timeouts, error formatting and logging behave identically everywhere, and
that a hung external tool can never hang the whole application.
"""

from __future__ import annotations

import asyncio
import os

import structlog

logger = structlog.get_logger()


class CommandError(RuntimeError):
    """Raised when an external backup command fails or times out."""


async def run_command(
    cmd: list[str],
    *,
    label: str,
    timeout: int,
    env: dict[str, str] | None = None,
    capture_stdout: bool = False,
) -> str:
    """Run *cmd*, raising :class:`CommandError` on failure.

    Args:
        cmd: Argument vector; never a shell string, so no quoting/injection
            concerns.
        label: Human-readable name used in logs and error messages.
        timeout: Seconds to wait before killing the process.
        env: Extra environment variables merged over the current environment.
        capture_stdout: When True the decoded stdout is returned.

    Returns:
        Decoded stdout (empty string when *capture_stdout* is False).
    """
    logger.info("backup_command_started", label=label)

    process = await asyncio.create_subprocess_exec(
        *cmd,
        env={**os.environ, **env} if env else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=timeout
        )
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        raise CommandError(f"{label} timed out after {timeout}s")

    if process.returncode != 0:
        detail = stderr.decode(errors="replace")[:500]
        raise CommandError(
            f"{label} exited with code {process.returncode}: {detail}"
        )

    logger.info("backup_command_completed", label=label)
    return stdout.decode(errors="replace") if capture_stdout else ""


def binary_available(binary: str) -> bool:
    """Return True when *binary* can be resolved on ``PATH``."""
    from shutil import which

    return which(binary) is not None
