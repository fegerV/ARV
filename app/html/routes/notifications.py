from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import false, or_, select, func
import structlog
from app.html.deps import get_html_db
from app.api.routes.auth import get_current_user_optional
from app.models.notification import Notification
from app.html.templating import templates
from app.html.utils import require_active_user, is_super_admin, forbidden_response
from app.core.config import settings

router = APIRouter()
logger = structlog.get_logger()


def _tenant_scope_condition(current_user):
    """Return a WHERE clause restricting notifications to the caller's tenant.

    ARV-032: ``Notification`` carries both ``company_id`` and ``user_id``, and
    the admin panel is reachable by every authenticated role — not only super
    admins. Without this filter any logged-in user could list, read and delete
    notifications belonging to other tenants.

    Super admins are unrestricted. Everyone else may only see rows addressed to
    their company or to themselves. A user with neither a company nor an id
    resolves to ``false`` — fail-closed, nothing is returned.
    """
    if is_super_admin(current_user):
        return None

    company_id = getattr(current_user, "company_id", None)
    user_id = getattr(current_user, "id", None)
    conditions = []
    if company_id is not None:
        conditions.append(Notification.company_id == company_id)
    if user_id is not None:
        conditions.append(Notification.user_id == user_id)
    return or_(*conditions) if conditions else false()


def _apply_tenant_scope(stmt, current_user):
    """Apply :func:`_tenant_scope_condition` to a SELECT/COUNT statement."""
    condition = _tenant_scope_condition(current_user)
    return stmt if condition is None else stmt.where(condition)


def _notification_is_visible(notification, current_user) -> bool:
    """Return True when *notification* belongs to the caller's tenant."""
    if is_super_admin(current_user):
        return True
    company_id = getattr(current_user, "company_id", None)
    user_id = getattr(current_user, "id", None)
    if company_id is not None and notification.company_id == company_id:
        return True
    return user_id is not None and notification.user_id == user_id


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
    redirect = require_active_user(current_user)
    if redirect:
        return redirect
    
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
        # Get total count (ARV-032: scoped to the caller's tenant)
        count_query = _apply_tenant_scope(
            select(func.count()).select_from(Notification), current_user
        )
        count_result = await db.execute(count_query)
        total_count = count_result.scalar() or 0
        
        # Calculate pagination
        offset = (page - 1) * page_size
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
        
        # Get notifications (latest first), scoped to the caller's tenant
        stmt = _apply_tenant_scope(
            select(Notification).order_by(Notification.created_at.desc()).offset(offset).limit(page_size),
            current_user,
        )
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
        
        # ARV-032: deny cross-tenant reads of a notification by id.
        if not _notification_is_visible(notification_db, current_user):
            return forbidden_response("Access denied to this notification")
        
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
        
        # ARV-032: deny cross-tenant deletion of a notification by id.
        if not _notification_is_visible(notification, current_user):
            return JSONResponse(content={"error": "Access denied to this notification"}, status_code=403)
        
        # Delete notification
        await db.delete(notification)
        await db.commit()
        
        logger.info("notification_deleted", notification_id=notification_id)
        return JSONResponse(content={"status": "deleted"}, status_code=200)
        
    except Exception as e:
        logger.error("notification_delete_error", notification_id=notification_id, error=str(e), exc_info=True)
        return JSONResponse(content={"error": f"Failed to delete notification: {str(e)}"}, status_code=400)
