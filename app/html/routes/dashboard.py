from datetime import datetime, timezone, timedelta
from fastapi import Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.html.deps import get_html_db
from app.api.routes.auth import get_current_user_optional
from app.html.filters import datetime_format
from app.models.company import Company
from app.models.project import Project
from app.models.ar_content import ARContent
from app.models.ar_view_session import ARViewSession
import structlog

router = APIRouter()
logger = structlog.get_logger()

templates = Jinja2Templates(directory="templates")
# Add datetime filter to templates
templates.env.filters["datetime_format"] = datetime_format

@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_html_db),
    current_user=Depends(get_current_user_optional),
):
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Get basic statistics (lightweight queries)
        total_companies = await db.execute(select(func.count()).select_from(Company))
        total_companies_count = total_companies.scalar() or 0
        
        active_companies = await db.execute(
            select(func.count()).select_from(Company).where(Company.status == "active")
        )
        active_companies_count = active_companies.scalar() or 0
        
        total_projects = await db.execute(select(func.count()).select_from(Project))
        total_projects_count = total_projects.scalar() or 0
        
        active_projects = await db.execute(
            select(func.count()).select_from(Project).where(Project.status == "active")
        )
        active_projects_count = active_projects.scalar() or 0
        
        total_ar_content = await db.execute(select(func.count()).select_from(ARContent))
        total_ar_content_count = total_ar_content.scalar() or 0
        
        active_ar_content = await db.execute(
            select(func.count()).select_from(ARContent).where(ARContent.status == "active")
        )
        active_ar_content_count = active_ar_content.scalar() or 0
        
        # Total views (all-time) — sum of views_count from AR content
        total_views_q = await db.execute(
            select(func.coalesce(func.sum(ARContent.views_count), 0))
        )
        total_views_count = total_views_q.scalar() or 0

        # Views in last 30 days (from session records)
        # Use naive UTC to match the column type (DateTime without timezone)
        since = datetime.utcnow() - timedelta(days=30)
        views_30d = await db.execute(
            select(func.count()).select_from(ARViewSession).where(ARViewSession.created_at >= since)
        )
        views_30d_count = views_30d.scalar() or 0

        # If no sessions recorded yet, use total_views as fallback
        if views_30d_count == 0 and total_views_count > 0:
            views_30d_count = total_views_count

        # Get last 5 AR content items
        recent_ar_content_query = (
            select(ARContent)
            .order_by(desc(ARContent.created_at))
            .limit(5)
        )
        recent_ar_content_result = await db.execute(recent_ar_content_query)
        recent_ar_content_list = recent_ar_content_result.scalars().all()
        
        recent_content = []
        for content in recent_ar_content_list:
            recent_content.append({
                "id": content.id,
                "order_number": content.order_number,
                "status": content.status,
                "created_at": content.created_at,
                "views_count": content.views_count or 0,
            })
        
        dashboard_data = {
            "total_companies": total_companies_count,
            "active_companies": active_companies_count,
            "total_projects": total_projects_count,
            "active_projects": active_projects_count,
            "total_ar_content": total_ar_content_count,
            "active_ar_content": active_ar_content_count,
            "total_views": total_views_count,
            "views_30d": views_30d_count,
            "recent_content": recent_content,
        }
    except Exception as e:
        logger.error("dashboard_data_error", error=str(e), exc_info=True)
        dashboard_data = {
            "total_companies": 0,
            "active_companies": 0,
            "total_projects": 0,
            "active_projects": 0,
            "total_ar_content": 0,
            "active_ar_content": 0,
            "total_views": 0,
            "views_30d": 0,
            "recent_content": [],
        }

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            **dashboard_data,
        },
    )