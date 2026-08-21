"""HTML route dependencies and data retrieval functions.

Production data-fetching helpers for HTML routes.  All functions
delegate to the real API services and surface database errors —
no mock fallback is used.
"""

from typing import List, Dict, Any
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

import structlog

from app.models.user import User
from app.core.database import get_db
from app.api.routes.auth import get_current_active_user
from app.api.routes.companies import list_companies, get_company
from app.api.routes.projects import list_projects, get_project
from app.api.routes.ar_content import list_all_ar_content, get_ar_content_by_id
from app.api.routes.analytics import analytics_summary

logger = structlog.get_logger()


async def get_dashboard_data(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_user)) -> Dict[str, Any]:
    """Get dashboard data from real services.

    Queries are run sequentially: AsyncSession does not support concurrent use.
    """
    analytics_result = await analytics_summary(db=db)
    companies_result = await list_companies(page=1, page_size=100, db=db, current_user=current_user)
    ar_content_result = await list_all_ar_content(page=1, page_size=100, db=db)

    dashboard_data = dict(analytics_result)
    companies = [dict(item) for item in companies_result.items]
    ar_content = [dict(item) for item in ar_content_result.items]

    return {
        "dashboard_data": dashboard_data,
        "companies": companies,
        "ar_content": ar_content,
    }


async def get_companies_list(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_user)) -> List[Dict[str, Any]]:
    """Get companies list from real services."""
    result = await list_companies(page=1, page_size=10, db=db, current_user=current_user)
    return [dict(item) for item in result.items]


async def get_company_detail(company_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_user)) -> Dict[str, Any]:
    """Get company detail from real services."""
    from app.schemas.company_api import CompanyDetail as CompanySchema
    company = await get_company(company_id, db)
    return CompanySchema.model_validate(company).dict()


async def get_ar_content_list(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_user)) -> Dict[str, Any]:
    """Get AR content list from real services."""
    result = await list_all_ar_content(page=1, page_size=10, db=db)
    ar_content_list = [dict(item) for item in result.items]

    unique_companies = list(set(item.get('company_name', '') for item in ar_content_list if item.get('company_name')))
    unique_statuses = list(set(item.get('status', '') for item in ar_content_list if item.get('status')))

    return {
        "ar_content_list": ar_content_list,
        "unique_companies": unique_companies,
        "unique_statuses": unique_statuses,
    }


async def get_ar_content_detail(ar_content_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_user)) -> Dict[str, Any]:
    """Get AR content detail from real services."""
    result = await get_ar_content_by_id(ar_content_id, db)
    ar_content = dict(result)

    if 'created_at' in ar_content and ar_content['created_at']:
        ar_content['created_at'] = ar_content['created_at'].isoformat()
    if 'updated_at' in ar_content and ar_content['updated_at']:
        ar_content['updated_at'] = ar_content['updated_at'].isoformat()

    return ar_content


async def get_ar_content_create_data(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_user)) -> Dict[str, Any]:
    """Get data for AR content creation page from real services.

    Queries are run sequentially: AsyncSession does not support concurrent use.
    """
    companies_result = await list_companies(page=1, page_size=100, db=db, current_user=current_user)
    projects_result = await list_projects(page=1, page_size=100, db=db, current_user=current_user)

    companies = [dict(item) for item in companies_result.items]
    projects = [dict(item) for item in projects_result.items]

    return {
        "companies": companies,
        "projects": projects,
    }


async def get_projects_list(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_user)) -> List[Dict[str, Any]]:
    """Get projects list from real services."""
    result = await list_projects(page=1, page_size=10, db=db, current_user=current_user)
    return [dict(item) for item in result.items]


async def get_project_detail(project_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_user)) -> Dict[str, Any]:
    """Get project detail from real services."""
    project = await get_project(project_id, db)
    return dict(project)


async def get_project_create_data(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_active_user)) -> List[Dict[str, Any]]:
    """Get data for project creation page from real services."""
    companies_result = await list_companies(page=1, page_size=100, db=db, current_user=current_user)
    return [dict(item) for item in companies_result.items]
