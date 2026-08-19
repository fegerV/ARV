"""Tests for IDOR/BOLA authorization checks."""
from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps_authz import (
    _get_user_company_ids,
    require_company_access,
    require_company_access_optional,
    require_resource_access,
)
from app.models.company import Company
from app.models.user import User


class _FakeUser:
    def __init__(self, id: int, company_id: int | None, is_super_admin: bool = False, is_active: bool = True):
        self.id = id
        self.company_id = company_id
        self.is_super_admin = is_super_admin
        self.is_active = is_active


class _FakeDb:
    def __init__(self, company_map=None):
        self.company_map = company_map or {}

    async def get(self, model, pk):
        return self.company_map.get(pk)


@pytest.mark.asyncio
async def test_super_admin_has_access_to_all_companies():
    user = _FakeUser(id=1, company_id=None, is_super_admin=True)
    result = await _get_user_company_ids(None, user)
    assert result is None


@pytest.mark.asyncio
async def test_user_without_company_has_access_to_all():
    user = _FakeUser(id=2, company_id=None, is_super_admin=False)
    result = await _get_user_company_ids(None, user)
    assert result is None


@pytest.mark.asyncio
async def test_regular_user_has_access_only_to_own_company():
    user = _FakeUser(id=3, company_id=5, is_super_admin=False)
    result = await _get_user_company_ids(None, user)
    assert result == {5}


@pytest.mark.asyncio
async def test_require_company_access_super_admin():
    user = _FakeUser(id=1, company_id=None, is_super_admin=True)
    company = Company(id=10, name="Test")
    db = _FakeDb(company_map={10: company})

    result = await require_company_access(10, db, user)
    assert result.id == 10


@pytest.mark.asyncio
async def test_require_company_access_regular_user_own_company():
    user = _FakeUser(id=3, company_id=5, is_super_admin=False)
    company = Company(id=5, name="Test")
    db = _FakeDb(company_map={5: company})

    result = await require_company_access(5, db, user)
    assert result.id == 5


@pytest.mark.asyncio
async def test_require_company_access_regular_user_other_company():
    user = _FakeUser(id=3, company_id=5, is_super_admin=False)
    company = Company(id=10, name="Test")
    db = _FakeDb(company_map={10: company})

    with pytest.raises(HTTPException) as exc_info:
        await require_company_access(10, db, user)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_company_access_company_not_found():
    user = _FakeUser(id=3, company_id=5, is_super_admin=False)
    db = _FakeDb(company_map={})

    with pytest.raises(HTTPException) as exc_info:
        await require_company_access(99, db, user)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_require_resource_access_regular_user_own_resource():
    user = _FakeUser(id=3, company_id=5, is_super_admin=False)
    result = await require_resource_access(5, db=None, current_user=user)
    assert result.id == 3


@pytest.mark.asyncio
async def test_require_resource_access_regular_user_other_resource():
    user = _FakeUser(id=3, company_id=5, is_super_admin=False)
    with pytest.raises(HTTPException) as exc_info:
        await require_resource_access(10, db=None, current_user=user)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_company_access_optional_returns_none_for_no_user():
    result = await require_company_access_optional(10, db=None, current_user=None)
    assert result == (None, None)


@pytest.mark.asyncio
async def test_require_company_access_optional_company_not_found():
    user = _FakeUser(id=3, company_id=5, is_super_admin=False)
    db = _FakeDb(company_map={})
    result = await require_company_access_optional(99, db, user)
    assert result[0] is None
    assert result[1].id == 3


@pytest.mark.asyncio
async def test_require_company_access_optional_denies_other_company():
    user = _FakeUser(id=3, company_id=5, is_super_admin=False)
    company = Company(id=10, name="Test")
    db = _FakeDb(company_map={10: company})
    with pytest.raises(HTTPException) as exc_info:
        await require_company_access_optional(10, db, user)
    assert exc_info.value.status_code == 403
