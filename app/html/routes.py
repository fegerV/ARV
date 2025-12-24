"""HTML routes for the application."""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.api.routes.auth import get_current_active_user, get_current_user_optional
from app.core.database import get_db
from app.html.depends import (
    get_dashboard_data, get_companies_list, get_company_detail, get_ar_content_list,
    get_ar_content_detail, get_ar_content_create_data, get_projects_list,
    get_project_detail, get_project_create_data, get_storage_data,
    get_analytics_data, get_notifications_data, get_settings_data
)
from app.mock_data import UNIQUE_VALUES_MOCK_DATA

# Jinja2 templates
from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="templates")

# Create router for HTML routes
router = APIRouter()

# Admin dashboard route
@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    """Admin dashboard page."""
    data = await get_dashboard_data(db, current_user)
    
    context = {
        "request": request,
        "current_user": current_user,
        "total_views": data["dashboard_data"].get("total_views", 0),
        "unique_sessions": data["dashboard_data"].get("unique_sessions", 0),
        "active_content": data["dashboard_data"].get("active_content", 0),
        "storage_used_gb": data["dashboard_data"].get("storage_used_gb", 0),
        "active_companies": data["dashboard_data"].get("active_companies", 0),
        "active_projects": data["dashboard_data"].get("active_projects", 0),
        "revenue": data["dashboard_data"].get("revenue", "$0"),
        "uptime": data["dashboard_data"].get("uptime", "0%"),
        "companies": data["companies"],
        "ar_content": data["ar_content"]
    }
    return templates.TemplateResponse("dashboard/index.html", context)

# Admin login page
@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Admin login page."""
    from app.middleware.rate_limiter import limiter
    limiter.limit("5/minute")  # Rate limit to 5 requests per minute per IP
    
    context = {
        "request": request,
        "error": None,
        "locked_until": None,
        "attempts_left": None
    }
    return templates.TemplateResponse("auth/login.html", context)

# Main route redirect
@router.get("/", response_class=RedirectResponse)
async def root(current_user: User = Depends(get_current_user_optional)):
    if current_user:
        return RedirectResponse("/admin")
    return RedirectResponse("/admin/login")

# Companies routes
@router.get("/companies", response_class=HTMLResponse)
async def companies_list(request: Request, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    """Companies list page."""
    companies = await get_companies_list(db, current_user)
    
    context = {
        "request": request,
        "companies": companies,
        "current_user": current_user
    }
    return templates.TemplateResponse("companies/list.html", context)

@router.get("/companies/{company_id}", response_class=HTMLResponse)
async def company_detail(company_id: str, request: Request, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    """Company detail page."""
    company_data = await get_company_detail(int(company_id), db, current_user)
    
    context = {
        "request": request,
        "company": company_data,
        "current_user": current_user
    }
    return templates.TemplateResponse("companies/detail.html", context)

@router.get("/companies/create", response_class=HTMLResponse)
async def company_create(request: Request, current_user: User = Depends(get_current_active_user)):
    """Company create page."""
    context = {
        "request": request,
        "current_user": current_user
    }
    return templates.TemplateResponse("companies/form.html", context)

# AR Content routes
@router.get("/ar-content", response_class=HTMLResponse)
async def ar_content_list(request: Request, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    """AR Content list page."""
    data = await get_ar_content_list(db, current_user)
    
    # Get pagination parameters
    page = int(request.query_params.get("page", 0))
    page_size = int(request.query_params.get("page_size", 10))
    
    context = {
        "request": request,
        "ar_content_list": data["ar_content_list"],
        "unique_companies": data["unique_companies"],
        "unique_statuses": data["unique_statuses"],
        "page": page,
        "page_size": page_size,
        "total_count": len(data["ar_content_list"]),
        "total_pages": 1,
        "current_user": current_user
    }
    return templates.TemplateResponse("ar-content/list.html", context)

@router.get("/ar-content/{ar_content_id}", response_class=HTMLResponse)
async def ar_content_detail(ar_content_id: str, request: Request, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    """AR Content detail page."""
    ar_content = await get_ar_content_detail(int(ar_content_id), db, current_user)
    
    context = {
        "request": request,
        "ar_content": ar_content,
        "current_user": current_user
    }
    return templates.TemplateResponse("ar-content/detail.html", context)

@router.get("/ar-content/create", response_class=HTMLResponse)
async def ar_content_create(request: Request, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    """AR Content create page."""
    data = await get_ar_content_create_data(db, current_user)
    
    context = {
        "request": request,
        "companies": data["companies"],
        "projects": data["projects"],
        "current_user": current_user
    }
    return templates.TemplateResponse("ar-content/form.html", context)

# HTMX endpoints for dynamic updates
@router.post("/ar-content/{ar_content_id}/copy-link")
async def copy_ar_content_link(ar_content_id: str, request: Request):
    """HTMX endpoint to handle link copying."""
    # In a real implementation, this would copy the link to clipboard
    # For now, we'll just return a success message
    return HTMLResponse("<div class='fixed bottom-4 right-4 bg-green-500 text-white px-4 py-2 rounded shadow'>Link copied to clipboard</div>")

@router.get("/ar-content/{ar_content_id}/qr-code")
async def get_ar_content_qr_code(ar_content_id: str, request: Request):
    """HTMX endpoint to get QR code for AR content."""
    # In a real implementation, this would generate and return the QR code
    # For now, we'll return a placeholder
    return HTMLResponse(f"""
    <div class="flex flex-col items-center">
        <div class="bg-white p-4 rounded">
            <img src="https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=https://example.com/ar/{ar_content_id}" alt="QR Code">
        </div>
        <p class="mt-2 text-sm">https://example.com/ar/{ar_content_id}</p>
    </div>
    """)

@router.delete("/ar-content/{ar_content_id}")
async def delete_ar_content(ar_content_id: str, request: Request):
    """HTMX endpoint to delete AR content."""
    # In a real implementation, this would delete the AR content from the database
    # For now, we'll just return an empty list
    context = {
        "request": request,
        "ar_content_list": [],
        "unique_companies": [],
        "unique_statuses": [],
        "page": 0,
        "page_size": 10,
        "total_count": 0,
        "total_pages": 1
    }
    return templates.TemplateResponse("ar-content/list.html", context)

# Projects routes
@router.get("/projects", response_class=HTMLResponse)
async def projects_list(request: Request, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    """Projects list page."""
    projects = await get_projects_list(db, current_user)
    
    # Get pagination parameters from request
    page = int(request.query_params.get("page", 0))
    page_size = int(request.query_params.get("page_size", 10))
    
    # Calculate total pages
    total_count = len(projects)
    total_pages = max(1, (total_count + page_size - 1) // page_size)  # Ceiling division, ensure at least 1 page
    
    context = {
        "request": request,
        "projects": projects,
        "current_user": current_user,
        "page": page,
        "page_size": page_size,
        "total_count": total_count,
        "total_pages": total_pages
    }
    return templates.TemplateResponse("projects/list.html", context)

@router.get("/projects/{project_id}", response_class=HTMLResponse)
async def project_detail(project_id: str, request: Request, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    """Project detail page."""
    project_data = await get_project_detail(int(project_id), db, current_user)
    
    context = {
        "request": request,
        "project": project_data,
        "current_user": current_user
    }
    return templates.TemplateResponse("projects/detail.html", context)

@router.get("/projects/create", response_class=HTMLResponse)
async def project_create(request: Request, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)):
    """Project create page."""
    companies = await get_project_create_data(db, current_user)
    
    context = {
        "request": request,
        "companies": companies,
        "current_user": current_user
    }
    return templates.TemplateResponse("projects/form.html", context)

# Other routes
@router.get("/storage", response_class=HTMLResponse)
async def storage_page(request: Request, current_user: User = Depends(get_current_active_user)):
    """Storage page."""
    storage_info = get_storage_data()
    
    context = {
        "request": request,
        "storage_info": storage_info["storage_info"],
        "current_user": current_user
    }
    return templates.TemplateResponse("storage.html", context)

@router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request, current_user: User = Depends(get_current_active_user)):
    """Analytics page."""
    analytics_data = get_analytics_data()
    
    context = {
        "request": request,
        "analytics_data": analytics_data["analytics_data"],
        "current_user": current_user
    }
    return templates.TemplateResponse("analytics.html", context)

@router.get("/notifications", response_class=HTMLResponse)
async def notifications_page(request: Request, current_user: User = Depends(get_current_active_user)):
    """Notifications page."""
    notifications = get_notifications_data()
    
    context = {
        "request": request,
        "notifications": notifications,
        "total_count": len(notifications),
        "current_user": current_user
    }
    return templates.TemplateResponse("notifications.html", context)

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, current_user: User = Depends(get_current_active_user)):
    """Settings page."""
    settings = get_settings_data()
    
    context = {
        "request": request,
        "settings": settings["settings"],
        "current_user": current_user
    }
    return templates.TemplateResponse("settings.html", context)