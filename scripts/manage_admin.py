#!/usr/bin/env python3
"""Canonical admin user management script.

Replaces the legacy admin creation/reset scripts scattered across
``utilities/`` and ``scripts/legacy/``.

Usage:
    python scripts/manage_admin.py create   # create admin if missing, else update password
    python scripts/manage_admin.py reset     # reset existing admin password

The script reads the new password from the ``ADMIN_DEFAULT_PASSWORD``
environment variable and uses the application's current password hashing
scheme (pbkdf2_sha256 via passlib).
"""

from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.user import User
from sqlalchemy import select


ADMIN_EMAIL = "admin@vertexar.com"
ADMIN_FULL_NAME = "Vertex AR Admin"
ADMIN_ROLE = "admin"


async def _get_session() -> AsyncSession:
    return AsyncSessionLocal()


async def create_admin() -> bool:
    new_password = os.environ.get("ADMIN_DEFAULT_PASSWORD", "")
    if not new_password:
        print("Error: ADMIN_DEFAULT_PASSWORD environment variable is not set")
        return False

    async with await _get_session() as session:
        try:
            result = await session.execute(select(User).where(User.email == ADMIN_EMAIL))
            user = result.scalar_one_or_none()

            if user:
                print(f"Admin user already exists: {user.email}")
                user.hashed_password = get_password_hash(new_password)
                user.login_attempts = 0
                user.locked_until = None
                print(f"Password updated for {user.email}")
            else:
                user = User(
                    email=ADMIN_EMAIL,
                    hashed_password=get_password_hash(new_password),
                    full_name=ADMIN_FULL_NAME,
                    role=ADMIN_ROLE,
                    is_active=True,
                    login_attempts=0,
                )
                session.add(user)
                print(f"Created new admin user: {user.email}")

            await session.commit()
            return True
        except Exception as exc:
            print(f"Error creating/updating admin user: {exc}")
            return False


async def reset_admin_password() -> bool:
    new_password = os.environ.get("ADMIN_DEFAULT_PASSWORD", "")
    if not new_password:
        print("Error: ADMIN_DEFAULT_PASSWORD environment variable is not set")
        return False

    async with await _get_session() as session:
        try:
            result = await session.execute(select(User).where(User.email == ADMIN_EMAIL))
            user = result.scalar_one_or_none()

            if not user:
                print("Admin user not found!")
                return False

            user.hashed_password = get_password_hash(new_password)
            user.login_attempts = 0
            user.locked_until = None
            await session.commit()
            print(f"Password reset successfully for {user.email}")
            return True
        except Exception as exc:
            print(f"Error resetting password: {exc}")
            return False


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/manage_admin.py <create|reset>")
        return 1

    command = sys.argv[1].lower()
    if command == "create":
        success = asyncio.run(create_admin())
    elif command == "reset":
        success = asyncio.run(reset_admin_password())
    else:
        print(f"Unknown command: {command}")
        return 1

    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
