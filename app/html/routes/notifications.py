from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import structlog
from app.html.deps import get_html_db
from app.api.routes.auth import get_current_user_optional
from app.models.notification import Notification
from app.html.filters import datetime_format, tojson_filter
from app.core.config import settings

router = APIRouter()
logger = structlog.get_logger()

templates = Jinja2Templates(directory="templates")
# Add datetime filter to templates
templates.env.filters["datetime_format"] = datetime_format
# Add custom tojson filter (overrides default if exists)
templates.env.filters["tojson"] = tojson_filter


def _convert_data_for_template(data_dict):
    """Convert datetime fields for template rendering."""
    # Convert datetime to ISO string
    if "created_at" in data_dict and hasattr(data_dict["created_at"], "isoformat"):
        data_dict["created_at"] = data_dict["created_at"].isoformat()
    if "updated_at" in data_dict and hasattr(data_dict["updated_at"], "isoformat"):
        data_dict["updated_at"] = data_dict["updated_at"].isoformat()
    
    return data_dict


@router.get("/notifications", response_class=HTMLResponse)
async def notifications_page(
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db)
):
    """Notifications list page with pagination."""
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Get query parameters
    try:
        page = int(request.query_params.get('page', 1))
        if page < 1:
            page = 1
    except (ValueError, TypeError):
        page = 1
    
    try:
        page_size = int(request.query_params.get('page_size', 20))
        if page_size < 1 or page_size > 100:
            page_size = 20
    except (ValueError, TypeError):
        page_size = 20
    
    try:
        # Get total count
        count_query = select(func.count()).select_from(Notification)
        count_result = await db.execute(count_query)
        total_count = count_result.scalar() or 0
        
        # Calculate pagination
        offset = (page - 1) * page_size
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
        
        # Get notifications (latest first)
        stmt = select(Notification).order_by(Notification.created_at.desc()).offset(offset).limit(page_size)
        result = await db.execute(stmt)
        notifications_db = result.scalars().all()
        
        # Transform database notifications to template format
        notifications = []
        for n in notifications_db:
            try:
                meta = dict(n.notification_metadata or {})
                
                notification = {
                    "id": n.id,
                    "title": n.subject or meta.get("title") or (n.notification_type.replace("_", " ").title() if n.notification_type else "Notification"),
                    "message": n.message or "",
                    "created_at": n.created_at,  # Pass datetime object - filter will handle it
                    "is_read": bool(meta.get("is_read", False)),
                    "company_name": meta.get("company_name"),
                    "project_name": meta.get("project_name"),
                    "ar_content_name": meta.get("ar_content_name"),
                    "notification_type": n.notification_type or "unknown",
                }
                notifications.append(notification)
            except Exception as e:
                logger.warning("error_processing_notification",
                             notification_id=getattr(n, 'id', None),
                             error=str(e))
                continue
        
    except Exception as e:
        logger.error("notifications_list_error", error=str(e), exc_info=True)
        notifications = []
        total_count = 0
        total_pages = 1
        page = 1
    
    try:
        context = {
            "request": request,
            "notifications": notifications,
            "total_count": total_count,
            "total_pages": total_pages,
            "page": page,
            "page_size": page_size,
            "current_user": current_user
        }
        return templates.TemplateResponse("notifications.html", context)
    except Exception as e:
        logger.error("notifications_template_error", 
                    error=str(e), 
                    error_type=type(e).__name__,
                    exc_info=True)
        # Return error page
        error_context = {
            "request": request,
            "notifications": [],
            "total_count": 0,
            "total_pages": 1,
            "page": 1,
            "page_size": 20,
            "current_user": current_user,
            "error_message": str(e) if settings.DEBUG else "An error occurred while loading notifications."
        }
        return templates.TemplateResponse("notifications.html", error_context, status_code=500)


@router.get("/notifications/{notification_id}", response_class=HTMLResponse)
async def notification_detail(
    notification_id: int,
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db)
):
    """Notification detail page."""
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Get notification
        stmt = select(Notification).where(Notification.id == notification_id)
        result = await db.execute(stmt)
        notification_db = result.scalar_one_or_none()
        
        if not notification_db:
            return RedirectResponse(url="/notifications", status_code=303)
        
        meta = dict(notification_db.notification_metadata or {})
        notification = {
            "id": notification_db.id,
            "title": notification_db.subject or meta.get("title") or notification_db.notification_type.replace("_", " ").title(),
            "message": notification_db.message or "",
            "created_at": notification_db.created_at.isoformat() if notification_db.created_at else None,
            "is_read": bool(meta.get("is_read", False)),
            "company_name": meta.get("company_name"),
            "project_name": meta.get("project_name"),
            "ar_content_name": meta.get("ar_content_name"),
            "notification_type": notification_db.notification_type,
        }
        
    except Exception as e:
        logger.error("notification_detail_error", error=str(e), exc_info=True)
        return RedirectResponse(url="/notifications", status_code=303)
    
    context = {
        "request": request,
        "notification": notification,
        "current_user": current_user
    }
    return templates.TemplateResponse("notifications/detail.html", context)


@router.delete("/notifications/{notification_id}")
async def notification_delete(
    notification_id: int,
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db)
):
    """Delete notification."""
    if not current_user:
        return JSONResponse(content={"error": "Unauthorized"}, status_code=401)
    
    if not current_user.is_active:
        return JSONResponse(content={"error": "Unauthorized"}, status_code=401)
    
    try:
        # Get notification
        stmt = select(Notification).where(Notification.id == notification_id)
        result = await db.execute(stmt)
        notification = result.scalar_one_or_none()
        
        if not notification:
            return JSONResponse(content={"error": "Notification not found"}, status_code=404)
        
        # Delete notification
        db.delete(notification)
        await db.commit()
        
        logger.info("notification_deleted", notification_id=notification_id)
        return JSONResponse(content={"status": "deleted"}, status_code=200)
        
    except Exception as e:
        logger.error("notification_delete_error", notification_id=notification_id, error=str(e), exc_info=True)
        return JSONResponse(content={"error": f"Failed to delete notification: {str(e)}"}, status_code=400)