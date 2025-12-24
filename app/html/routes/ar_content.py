from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.templating import Jinja2Templates
from app.models.user import User
from app.api.routes.ar_content import list_all_ar_content, get_ar_content_by_id_legacy
from app.api.routes.companies import list_companies
from app.api.routes.projects import list_projects
from app.html.deps import get_html_db, CurrentActiveUser
from app.html.mock import MOCK_AR_CONTENT, AR_CONTENT_DETAIL_MOCK_DATA, PROJECT_CREATE_MOCK_DATA
from app.html.filters import datetime_format

router = APIRouter()

templates = Jinja2Templates(directory="templates")
# Add datetime filter to templates
templates.env.filters["datetime_format"] = datetime_format

@router.get("/ar-content", response_class=HTMLResponse)
async def ar_content_list(
    request: Request,
    current_user=CurrentActiveUser,
    db: AsyncSession = Depends(get_html_db)
):
    """AR Content list page."""
    try:
        result = await list_all_ar_content(page=1, page_size=10, db=db)
        ar_content_list = [dict(item) for item in result.items]
        
        # Extract unique companies and statuses for filters
        unique_companies = list(set(item.get('company_name', '') for item in ar_content_list if item.get('company_name')))
        unique_statuses = list(set(item.get('status', '') for item in ar_content_list if item.get('status')))
    except Exception:
        # fallback to mock data
        ar_content_list = MOCK_AR_CONTENT
        unique_companies = PROJECT_CREATE_MOCK_DATA["companies"]
        unique_statuses = ["ready", "processing", "pending", "failed"]
    
    # Get pagination parameters
    page = int(request.query_params.get("page", 0))
    page_size = int(request.query_params.get("page_size", 10))
    
    context = {
        "request": request,
        "ar_content_list": ar_content_list,
        "unique_companies": unique_companies,
        "unique_statuses": unique_statuses,
        "page": page,
        "page_size": page_size,
        "total_count": len(ar_content_list),
        "total_pages": 1,
        "current_user": current_user
    }
    return templates.TemplateResponse("ar-content/list.html", context)

@router.get("/ar-content/{ar_content_id}", response_class=HTMLResponse)
async def ar_content_detail(
    ar_content_id: str,
    request: Request,
    current_user=CurrentActiveUser,
    db: AsyncSession = Depends(get_html_db)
):
    """AR Content detail page."""
    try:
        result = await get_ar_content_by_id_legacy(int(ar_content_id), db)
        ar_content = dict(result)
        
        # Convert datetime objects to strings for template
        if 'created_at' in ar_content and ar_content['created_at']:
            ar_content['created_at'] = ar_content['created_at'].isoformat()
        if 'updated_at' in ar_content and ar_content['updated_at']:
            ar_content['updated_at'] = ar_content['updated_at'].isoformat()
    except Exception:
        # fallback to mock data
        ar_content = {**AR_CONTENT_DETAIL_MOCK_DATA, "id": ar_content_id}
    
    context = {
        "request": request,
        "ar_content": ar_content,
        "current_user": current_user
    }
    return templates.TemplateResponse("ar-content/detail.html", context)

@router.get("/ar-content/create", response_class=HTMLResponse)
async def ar_content_create(
    request: Request,
    current_user=CurrentActiveUser,
    db: AsyncSession = Depends(get_html_db)
):
    """AR Content create page."""
    try:
        companies_task = list_companies(page=1, page_size=100, db=db, current_user=current_user)
        projects_task = list_projects(page=1, page_size=100, db=db, current_user=current_user)
        
        import asyncio
        companies_result, projects_result = await asyncio.gather(
            companies_task, projects_task, return_exceptions=True
        )
        
        if isinstance(companies_result, Exception):
            raise companies_result
        if isinstance(projects_result, Exception):
            raise projects_result
            
        companies = [dict(item) for item in companies_result.items]
        projects = [dict(item) for item in projects_result.items]
        
        data = {
            "companies": companies,
            "projects": projects
        }
    except Exception:
        # fallback to mock data
        data = PROJECT_CREATE_MOCK_DATA
    
    context = {
        "request": request,
        "companies": data["companies"],
        "projects": data["projects"],
        "current_user": current_user
    }
    return templates.TemplateResponse("ar-content/form.html", context)
