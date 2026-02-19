"""HTML route dependencies and data retrieval functions."""

from typing import List, Dict, Any, Optional
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

import structlog

from app.models.user import User
from app.core.database import get_db
from app.core.config import settings
from app.api.routes.auth import get_current_active_user
from app.api.routes.companies import list_companies, get_company
from app.api.routes.projects import list_projects, get_project
from app.api.routes.ar_content import list_all_ar_content, get_ar_content_by_id
from app.api.routes.analytics import analytics_summary
from app.mock_data import (
    DASHBOARD_MOCK_DATA, COMPANIES_MOCK_DATA, AR_CONTENT_MOCK_DATA,
    AR_CONTENT_DETAIL_MOCK_DATA, PROJECTS_MOCK_DATA, PROJECT_CREATE_MOCK_DATA,
    STORAGE_MOCK_DATA, ANALYTICS_MOCK_DATA, NOTIFICATIONS_MOCK_DATA, SETTINGS_MOCK_DATA
)


logger = structlog.get_logger()


def _raise_or_use_mock(error: Exception) -> None:
    """Raise in production; allow mock fallback in debug."""
    if settings.DEBUG:
        return
    logger.exception("html_data_fetch_failed", error=str(error))
    raise error


async def get_dashboard_data(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_user)) -> Dict[str, Any]:
    """Get dashboard data with fallback to mock data.
    Запросы выполняются последовательно: AsyncSession не поддерживает параллельное использование.
    """
    try:
        analytics_result = await analytics_summary(db=db)
        companies_result = await list_companies(page=1, page_size=100, db=db, current_user=current_user)
        ar_content_result = await list_all_ar_content(page=1, page_size=100, db=db)

        dashboard_data = dict(analytics_result)
        companies = [dict(item) for item in companies_result.items]
        ar_content = [dict(item) for item in ar_content_result.items]

        return {
            "dashboard_data": dashboard_data,
            "companies": companies,
            "ar_content": ar_content
        }
    except Exception as exc:
        _raise_or_use_mock(exc)
        return {
            "dashboard_data": DASHBOARD_MOCK_DATA,
            "companies": COMPANIES_MOCK_DATA,
            "ar_content": AR_CONTENT_MOCK_DATA
        }


async def get_companies_list(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_user)) -> List[Dict[str, Any]]:
    """Get companies list with fallback to mock data."""
    try:
        result = await list_companies(page=1, page_size=10, db=db, current_user=current_user)
        return [dict(item) for item in result.items]
    except Exception as exc:
        _raise_or_use_mock(exc)
        return COMPANIES_MOCK_DATA


async def get_company_detail(company_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_user)) -> Dict[str, Any]:
    """Get company detail with fallback to mock data."""
    try:
        from app.schemas.company import Company as CompanySchema
        company = await get_company(company_id, db)
        return CompanySchema.model_validate(company).dict()
    except Exception as exc:
        _raise_or_use_mock(exc)
        return {**AR_CONTENT_DETAIL_MOCK_DATA, "id": str(company_id)}


async def get_ar_content_list(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_user)) -> Dict[str, Any]:
    """Get AR content list with fallback to mock data."""
    try:
        result = await list_all_ar_content(page=1, page_size=10, db=db)
        ar_content_list = [dict(item) for item in result.items]
        
        # Extract unique companies and statuses for filters
        unique_companies = list(set(item.get('company_name', '') for item in ar_content_list if item.get('company_name')))
        unique_statuses = list(set(item.get('status', '') for item in ar_content_list if item.get('status')))
        
        return {
            "ar_content_list": ar_content_list,
            "unique_companies": unique_companies,
            "unique_statuses": unique_statuses
        }
    except Exception as exc:
        _raise_or_use_mock(exc)
        return {
            "ar_content_list": AR_CONTENT_MOCK_DATA,
            "unique_companies": PROJECT_CREATE_MOCK_DATA["companies"],
            "unique_statuses": ["ready", "processing", "pending", "failed"]
        }


async def get_ar_content_detail(ar_content_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_user)) -> Dict[str, Any]:
    """Get AR content detail with fallback to mock data."""
    try:
        result = await get_ar_content_by_id(ar_content_id, db)
        ar_content = dict(result)
        
        # Convert datetime objects to strings for template
        if 'created_at' in ar_content and ar_content['created_at']:
            ar_content['created_at'] = ar_content['created_at'].isoformat()
        if 'updated_at' in ar_content and ar_content['updated_at']:
            ar_content['updated_at'] = ar_content['updated_at'].isoformat()
            
        return ar_content
    except Exception as exc:
        _raise_or_use_mock(exc)
        return {**AR_CONTENT_DETAIL_MOCK_DATA, "id": str(ar_content_id)}


async def get_ar_content_create_data(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_user)) -> Dict[str, Any]:
    """Get data for AR content creation page with fallback to mock data.
    Запросы последовательно: AsyncSession не поддерживает параллельное использование.
    """
    try:
        companies_result = await list_companies(page=1, page_size=100, db=db, current_user=current_user)
        projects_result = await list_projects(page=1, page_size=100, db=db, current_user=current_user)

        companies = [dict(item) for item in companies_result.items]
        projects = [dict(item) for item in projects_result.items]

        return {
            "companies": companies,
            "projects": projects
        }
    except Exception as exc:
        _raise_or_use_mock(exc)
        return PROJECT_CREATE_MOCK_DATA


async def get_projects_list(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_user)) -> List[Dict[str, Any]]:
    """Get projects list with fallback to mock data."""
    try:
        result = await list_projects(page=1, page_size=10, db=db, current_user=current_user)
        return [dict(item) for item in result.items]
    except Exception as exc:
        _raise_or_use_mock(exc)
        return PROJECTS_MOCK_DATA


async def get_project_detail(project_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_user)) -> Dict[str, Any]:
    """Get project detail with fallback to mock data."""
    try:
        project = await get_project(project_id, db)
        return dict(project)
    except Exception as exc:
        _raise_or_use_mock(exc)
        return {**PROJECTS_MOCK_DATA[0], "id": str(project_id)}


async def get_project_create_data(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_user)) -> List[Dict[str, Any]]:
    """Get data for project creation page with fallback to mock data."""
    try:
        companies_result = await list_companies(page=1, page_size=100, db=db, current_user=current_user)
        return [dict(item) for item in companies_result.items]
    except Exception as exc:
        _raise_or_use_mock(exc)
        return PROJECT_CREATE_MOCK_DATA["companies"]


def get_storage_data() -> Dict[str, Any]:
    """Get storage data (no API call needed, using mock data)."""
    return STORAGE_MOCK_DATA


def get_analytics_data() -> Dict[str, Any]:
    """Get analytics data (no API call needed, using mock data)."""
    return ANALYTICS_MOCK_DATA


def get_notifications_data() -> List[Dict[str, Any]]:
    """Get notifications data (no API call needed, using mock data)."""
    return NOTIFICATIONS_MOCK_DATA


def get_settings_data() -> Dict[str, Any]:
    """Get settings data (no API call needed, using mock data)."""
    return SETTINGS_MOCK_DATA