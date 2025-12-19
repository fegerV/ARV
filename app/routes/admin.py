"""
Admin routes for serving HTML templates
"""
from fastapi import APIRouter, Depends, Request, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_async_session
from app.api.routes.auth import get_current_active_user, get_current_user_optional
from app.models.user import User
from app.models.company import Company
from app.models.project import Project
from app.models.ar_content import ARContent
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.schemas.ar_content import ARContentCreate, ARContentUpdate
from app.services.company import CompanyService
from app.services.project import ProjectService
from app.services.ar_content import ARContentService
from app.services.analytics import AnalyticsService
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/admin", tags=["Admin"])

# Initialize templates
templates = Jinja2Templates(directory="templates")


def get_templates_context(request: Request, current_user: Optional[User] = None):
    """Get common context for all templates"""
    return {
        "request": request,
        "current_user": current_user,
    }


# Authentication Routes
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Serve login page"""
    return templates.TemplateResponse(
        "auth/login.html",
        {"request": request}
    )


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Serve dashboard page"""
    context = get_templates_context(request, current_user)
    return templates.TemplateResponse("dashboard/index.html", context)


# Companies Routes
@router.get("/companies", response_class=HTMLResponse)
async def companies_list(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    status: Optional[str] = None
):
    """Serve companies list page"""
    context = get_templates_context(request, current_user)
    return templates.TemplateResponse("companies/list.html", context)


@router.get("/companies/new", response_class=HTMLResponse)
async def companies_new(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Serve new company form page"""
    context = get_templates_context(request, current_user)
    return templates.TemplateResponse("companies/form.html", context)


@router.get("/companies/{company_id}", response_class=HTMLResponse)
async def companies_detail(
    company_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Serve company detail page"""
    company_service = CompanyService(db)
    company = await company_service.get(company_id)
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    context = get_templates_context(request, current_user)
    context["company"] = company
    return templates.TemplateResponse("companies/detail.html", context)


@router.get("/companies/{company_id}/edit", response_class=HTMLResponse)
async def companies_edit(
    company_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Serve edit company form page"""
    company_service = CompanyService(db)
    company = await company_service.get(company_id)
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    context = get_templates_context(request, current_user)
    context["company"] = company
    return templates.TemplateResponse("companies/form.html", context)


# Projects Routes
@router.get("/projects", response_class=HTMLResponse)
async def projects_list(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    company_id: Optional[str] = None
):
    """Serve projects list page"""
    context = get_templates_context(request, current_user)
    return templates.TemplateResponse("projects/list.html", context)


@router.get("/projects/new", response_class=HTMLResponse)
async def projects_new(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
    company_id: Optional[str] = None
):
    """Serve new project form page"""
    context = get_templates_context(request, current_user)
    context["company_id"] = company_id
    return templates.TemplateResponse("projects/form.html", context)


@router.get("/companies/{company_id}/projects", response_class=HTMLResponse)
async def company_projects_list(
    company_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Serve company projects list page"""
    company_service = CompanyService(db)
    company = await company_service.get(company_id)
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    context = get_templates_context(request, current_user)
    context["company"] = company
    return templates.TemplateResponse("projects/list.html", context)


@router.get("/companies/{company_id}/projects/new", response_class=HTMLResponse)
async def company_projects_new(
    company_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Serve new project form page for specific company"""
    company_service = CompanyService(db)
    company = await company_service.get(company_id)
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    context = get_templates_context(request, current_user)
    context["company"] = company
    return templates.TemplateResponse("projects/form.html", context)


# AR Content Routes
@router.get("/ar-content", response_class=HTMLResponse)
async def ar_content_list(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    project_id: Optional[str] = None,
    status: Optional[str] = None
):
    """Serve AR content list page"""
    context = get_templates_context(request, current_user)
    return templates.TemplateResponse("ar-content/list.html", context)


@router.get("/ar-content/new", response_class=HTMLResponse)
async def ar_content_new(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
    project_id: Optional[str] = None
):
    """Serve new AR content form page"""
    context = get_templates_context(request, current_user)
    context["project_id"] = project_id
    return templates.TemplateResponse("ar-content/form.html", context)


@router.get("/ar-content/{ar_content_id}", response_class=HTMLResponse)
async def ar_content_detail(
    ar_content_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Serve AR content detail page"""
    ar_content_service = ARContentService(db)
    ar_content = await ar_content_service.get(ar_content_id)
    
    if not ar_content:
        raise HTTPException(status_code=404, detail="AR content not found")
    
    context = get_templates_context(request, current_user)
    context["ar_content"] = ar_content
    return templates.TemplateResponse("ar-content/detail.html", context)


@router.get("/projects/{project_id}/content", response_class=HTMLResponse)
async def project_ar_content_list(
    project_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Serve project AR content list page"""
    project_service = ProjectService(db)
    project = await project_service.get(project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    context = get_templates_context(request, current_user)
    context["project"] = project
    return templates.TemplateResponse("ar-content/list.html", context)


@router.get("/projects/{project_id}/content/new", response_class=HTMLResponse)
async def project_ar_content_new(
    project_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Serve new AR content form page for specific project"""
    project_service = ProjectService(db)
    project = await project_service.get(project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    context = get_templates_context(request, current_user)
    context["project"] = project
    return templates.TemplateResponse("ar-content/form.html", context)


# Analytics Routes
@router.get("/analytics", response_class=HTMLResponse)
async def analytics(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Serve analytics page"""
    context = get_templates_context(request, current_user)
    return templates.TemplateResponse("analytics/index.html", context)


# Storage Routes
@router.get("/storage", response_class=HTMLResponse)
async def storage(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Serve storage management page"""
    context = get_templates_context(request, current_user)
    return templates.TemplateResponse("storage/index.html", context)


# Notifications Routes
@router.get("/notifications", response_class=HTMLResponse)
async def notifications(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Serve notifications page"""
    context = get_templates_context(request, current_user)
    return templates.TemplateResponse("notifications/index.html", context)


# Settings Routes
@router.get("/settings", response_class=HTMLResponse)
async def settings(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Serve settings page"""
    context = get_templates_context(request, current_user)
    return templates.TemplateResponse("settings/index.html", context)


# Profile Routes
@router.get("/profile", response_class=HTMLResponse)
async def profile(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Serve user profile page"""
    context = get_templates_context(request, current_user)
    return templates.TemplateResponse("profile/index.html", context)