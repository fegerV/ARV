from typing import Optional
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.routes.auth import get_current_active_user
from app.models.user import User
from app.models.company import Company


def is_super_admin(user: User | None) -> bool:
    """Return True only when the user is explicitly flagged as a super admin."""
    return bool(getattr(user, "is_super_admin", False))


def user_can_access_company(user: User | None, company_id: int | None) -> bool:
    """Return True when *user* is allowed to access resources of *company_id*.

    Access rules (fail-closed):
      * super admins may access any company;
      * regular users may access only their own company;
      * a user without a company assignment has **no** company access.
    """
    if user is None:
        return False
    if is_super_admin(user):
        return True
    user_company_id = getattr(user, "company_id", None)
    if user_company_id is None:
        return False
    if company_id is None:
        return False
    return user_company_id == company_id


def require_super_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Dependency that allows only super admins (global administrators)."""
    if not is_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Super admin access required")
    return current_user


def ensure_authenticated_user(user) -> User:
    """Fail-closed guard for handlers that are also invoked directly.

    When a route handler is called as a plain Python function (e.g. from an
    HTML route) its ``Depends(...)`` defaults are *not* resolved, so a
    dependency object would be passed instead of a real ``User``. This helper
    rejects anything that is not a persisted user row.
    """
    if not isinstance(user, User):
        raise HTTPException(status_code=403, detail="Authentication required")
    return user


async def _get_user_company_ids(db: AsyncSession, user: User) -> set[int] | None:
    """Get all company IDs the user has access to.

    Returns ``None`` for super admins (meaning "all companies"), an empty set
    for users without a company assignment (meaning "none"), and a single-item
    set for regular users.
    """
    if is_super_admin(user):
        return None  # super admin has access to all companies
    company_id = getattr(user, "company_id", None)
    if company_id is None:
        return set()  # no company -> no access (fail closed)
    return {company_id}


async def require_company_access(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Company:
    """Dependency that verifies the current user has access to the company."""
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if not user_can_access_company(current_user, company_id):
        raise HTTPException(status_code=403, detail="Access denied to this company")

    return company


async def require_company_access_optional(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_active_user),
) -> tuple[Company | None, User | None]:
    """Optional version that returns (company, user) or (None, None)."""
    if current_user is None:
        return None, None

    company = await db.get(Company, company_id)
    if not company:
        return None, current_user

    if not user_can_access_company(current_user, company_id):
        raise HTTPException(status_code=403, detail="Access denied to this company")

    return company, current_user


async def require_resource_access(
    resource_company_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Dependency that verifies the current user has access to a resource's company."""
    if not user_can_access_company(current_user, resource_company_id):
        raise HTTPException(status_code=403, detail="Access denied to this resource")

    return current_user
