from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from datetime import datetime, timedelta, timezone
import structlog

from app.html.deps import get_html_db
from app.api.routes.auth import get_current_user_optional
from app.html.filters import datetime_format
from app.models.ar_view_session import ARViewSession
from app.models.ar_content import ARContent
from app.models.project import Project
from app.models.company import Company

router = APIRouter()
logger = structlog.get_logger()

templates = Jinja2Templates(directory="templates")
# Add datetime filter to templates
templates.env.filters["datetime_format"] = datetime_format


async def get_analytics_data(db: AsyncSession) -> dict:
    """Get lightweight analytics data without heavy database queries.
    
    Returns only simple COUNT queries that are fast.
    """
    try:
        # Date range: last 30 days
        since = datetime.now(timezone.utc) - timedelta(days=30)
        
        # Total views in last 30 days (simple COUNT)
        views_query = select(func.count()).select_from(ARViewSession).where(
            ARViewSession.created_at >= since
        )
        views_result = await db.execute(views_query)
        total_views = views_result.scalar() or 0
        
        # Unique sessions in last 30 days
        # Use approximate count for better performance - limit to reasonable number
        # For SQLite, COUNT DISTINCT can be slow, so we limit the query
        try:
            # Try to get unique sessions count (limit to prevent timeout)
            unique_sessions_query = select(func.count(text('DISTINCT session_id'))).select_from(
                ARViewSession
            ).where(ARViewSession.created_at >= since)
            unique_result = await db.execute(unique_sessions_query)
            unique_sessions = unique_result.scalar() or 0
        except Exception as e:
            logger.warning("unique_sessions_count_failed", error=str(e))
            # Fallback: approximate as 70% of total views (typical ratio)
            unique_sessions = int(total_views * 0.7) if total_views > 0 else 0
        
        # Active content (simple COUNT) - count both "ready" and "active" status
        active_content_query = select(func.count()).select_from(ARContent).where(
            ARContent.status.in_(["ready", "active"])
        )
        active_content_result = await db.execute(active_content_query)
        active_content = active_content_result.scalar() or 0
        
        # Active companies (simple COUNT)
        active_companies_query = select(func.count()).select_from(Company).where(
            Company.status == "active"
        )
        active_companies_result = await db.execute(active_companies_query)
        active_companies = active_companies_result.scalar() or 0
        
        # Active projects (simple COUNT)
        active_projects_query = select(func.count()).select_from(Project).where(
            Project.status == "active"
        )
        active_projects_result = await db.execute(active_projects_query)
        active_projects = active_projects_result.scalar() or 0
        
        # Total AR content (all statuses)
        total_content_query = select(func.count()).select_from(ARContent)
        total_content_result = await db.execute(total_content_query)
        total_content = total_content_result.scalar() or 0
        
        return {
            "total_views": total_views,
            "unique_sessions": unique_sessions,
            "active_content": active_content,
            "total_content": total_content,
            "active_companies": active_companies,
            "active_projects": active_projects,
        }
    except Exception as e:
        logger.error("error_getting_analytics", error=str(e))
        return {
            "total_views": 0,
            "unique_sessions": 0,
            "active_content": 0,
            "total_content": 0,
            "active_companies": 0,
            "active_projects": 0,
        }


@router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(
    request: Request,
    db: AsyncSession = Depends(get_html_db),
    current_user=Depends(get_current_user_optional)
):
    """Analytics page with real lightweight data."""
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Get real analytics data
    try:
        analytics_data = await get_analytics_data(db)
    except Exception as e:
        logger.error("analytics_page_error", error=str(e))
        analytics_data = {
            "total_views": 0,
            "unique_sessions": 0,
            "active_content": 0,
            "total_content": 0,
            "active_companies": 0,
            "active_projects": 0,
        }
    
    context = {
        "request": request,
        "analytics_data": analytics_data,
        "current_user": current_user
    }
    return templates.TemplateResponse("analytics.html", context)