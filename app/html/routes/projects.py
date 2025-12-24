from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.templating import Jinja2Templates
from app.models.user import User
from app.api.routes.projects import list_projects, get_project
from app.html.deps import get_html_db, CurrentActiveUser
from app.html.mock import MOCK_PROJECTS, PROJECT_CREATE_MOCK_DATA
from app.html.filters import datetime_format

router = APIRouter()

templates = Jinja2Templates(directory="templates")
# Add datetime filter to templates
templates.env.filters["datetime_format"] = datetime_format

@router.get("/projects", response_class=HTMLResponse)
async def projects_list(
    request: Request,
    current_user=CurrentActiveUser,
    db: AsyncSession = Depends(get_html_db)
):
    """Projects list page."""
    try:
        result = await list_projects(page=1, page_size=10, db=db, current_user=current_user)
        projects = [dict(item) for item in result.items]
    except Exception:
        # fallback to mock data
        projects = MOCK_PROJECTS
    
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
async def project_detail(
    project_id: str,
    request: Request,
    current_user=CurrentActiveUser,
    db: AsyncSession = Depends(get_html_db)
):
    """Project detail page."""
    try:
        project = await get_project(int(project_id), db)
        project_data = dict(project)
    except Exception:
        # fallback to mock data
        project_data = {**MOCK_PROJECTS[0], "id": project_id}
    
    context = {
        "request": request,
        "project": project_data,
        "current_user": current_user
    }
    return templates.TemplateResponse("projects/detail.html", context)

@router.get("/projects/create", response_class=HTMLResponse)
async def project_create(
    request: Request,
    current_user=CurrentActiveUser,
    db: AsyncSession = Depends(get_html_db)
):
    """Project create page."""
    try:
        from app.api.routes.companies import list_companies
        companies_result = await list_companies(page=1, page_size=100, db=db, current_user=current_user)
        companies = [dict(item) for item in companies_result.items]
    except Exception:
        # fallback to mock data
        companies = PROJECT_CREATE_MOCK_DATA["companies"]
    
    context = {
        "request": request,
        "companies": companies,
        "current_user": current_user
    }
    return templates.TemplateResponse("projects/form.html", context)