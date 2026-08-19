from typing import Optional
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.routes.auth import get_current_active_user
from app.models.user import User
from app.models.company import Company


async def _get_user_company_ids(db: AsyncSession, user: User) -> set[int] | None:
    """Get all company IDs the user has access to."""
    if getattr(user, 'is_super_admin', False) or getattr(user, 'company_id', None) is None:
        return None  # super admin has access to all
    return {user.company_id}


async def require_company_access(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Company:
    """Dependency that verifies the current user has access to the company."""
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if getattr(current_user, 'is_super_admin', False) or getattr(current_user, 'company_id', None) is None:
        return company

    if current_user.company_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied to this company")

    return company


async def require_company_access_optional(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_active_user),
) -> tuple[Optional[Company], Optional[User]]:
    """Optional version that returns (company, user) or (None, None)."""
    if current_user is None:
        return None, None

    company = await db.get(Company, company_id)
    if not company:
        return None, current_user

    if getattr(current_user, 'is_super_admin', False) or getattr(current_user, 'company_id', None) is None:
        return company, current_user

    if current_user.company_id != company_id:
        raise HTTPException(status_code=403, detail="Access denied to this company")

    return company, current_user


async def require_resource_access(
    resource_company_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Dependency that verifies the current user has access to a resource's company."""
    if getattr(current_user, 'is_super_admin', False) or getattr(current_user, 'company_id', None) is None:
        return current_user

    if current_user.company_id != resource_company_id:
        raise HTTPException(status_code=403, detail="Access denied to this resource")

    return current_user
