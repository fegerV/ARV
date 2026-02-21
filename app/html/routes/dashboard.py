from datetime import datetime, timedelta
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
        since = datetime.utcnow() - timedelta(days=30)

        # AsyncSession не поддерживает параллельные операции — выполняем запросы последовательно.
        r_companies = await db.execute(select(func.count()).select_from(Company))
        total_companies_count = r_companies.scalar() or 0
        r_active_companies = await db.execute(
            select(func.count()).select_from(Company).where(Company.status == "active")
        )
        active_companies_count = r_active_companies.scalar() or 0
        r_projects = await db.execute(select(func.count()).select_from(Project))
        total_projects_count = r_projects.scalar() or 0
        r_active_projects = await db.execute(
            select(func.count()).select_from(Project).where(Project.status == "active")
        )
        active_projects_count = r_active_projects.scalar() or 0
        r_ar = await db.execute(select(func.count()).select_from(ARContent))
        total_ar_content_count = r_ar.scalar() or 0
        r_active_ar = await db.execute(
            select(func.count()).select_from(ARContent).where(ARContent.status == "active")
        )
        active_ar_content_count = r_active_ar.scalar() or 0
        r_views = await db.execute(select(func.coalesce(func.sum(ARContent.views_count), 0)))
        total_views_count = r_views.scalar() or 0
        r_views_30 = await db.execute(
            select(func.count()).select_from(ARViewSession).where(ARViewSession.created_at >= since)
        )
        views_30d_count = r_views_30.scalar() or 0
        recent_rows_result = await db.execute(
            select(
                ARContent.id,
                ARContent.order_number,
                ARContent.status,
                ARContent.created_at,
                ARContent.views_count,
            )
            .order_by(desc(ARContent.created_at))
            .limit(5)
        )

        if views_30d_count == 0 and total_views_count > 0:
            views_30d_count = total_views_count

        recent_content = [
            {
                "id": row.id,
                "order_number": row.order_number,
                "status": row.status,
                "created_at": row.created_at,
                "views_count": row.views_count or 0,
            }
            for row in recent_rows_result.all()
        ]
        
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