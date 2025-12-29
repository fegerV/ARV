from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.html.deps import get_html_db
from app.api.routes.auth import get_current_user_optional
from app.models.notification import Notification
from app.html.filters import datetime_format

router = APIRouter()

templates = Jinja2Templates(directory="templates")
# Add datetime filter to templates
templates.env.filters["datetime_format"] = datetime_format

@router.get("/notifications", response_class=HTMLResponse)
async def notifications_page(
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db)
):
    """Notifications page."""
    if not current_user:
        # Redirect to login page if user is not authenticated
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        # Redirect to login page if user is not active
        return RedirectResponse(url="/admin/login", status_code=303)
    # Get notifications from database
    stmt = select(Notification).order_by(Notification.created_at.desc()).limit(50)
    result = await db.execute(stmt)
    notifications_db = result.scalars().all()
    
    # Transform database notifications to template format
    notifications = []
    for n in notifications_db:
        meta = dict(n.notification_metadata or {})
        
        notification = {
            "id": n.id,
            "title": n.subject or meta.get("title") or n.notification_type.replace("_", " ").title(),
            "message": n.message or "",
            "created_at": n.created_at,
            "is_read": bool(meta.get("is_read", False)),
            "company_name": meta.get("company_name"),
            "project_name": meta.get("project_name"),
            "ar_content_name": meta.get("ar_content_name"),
        }
        notifications.append(notification)
    
    context = {
        "request": request,
        "notifications": notifications,
        "total_count": len(notifications),
        "current_user": current_user
    }
    return templates.TemplateResponse("notifications.html", context)