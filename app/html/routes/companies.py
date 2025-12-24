from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.templating import Jinja2Templates
from app.models.user import User
from app.api.routes.companies import list_companies, get_company
from app.html.deps import get_html_db, CurrentActiveUser
from app.html.mock import MOCK_COMPANIES
from app.html.filters import datetime_format

router = APIRouter()

templates = Jinja2Templates(directory="templates")
# Add datetime filter to templates
templates.env.filters["datetime_format"] = datetime_format

@router.get("/companies", response_class=HTMLResponse)
async def companies_list(
    request: Request,
    current_user=CurrentActiveUser,
    db: AsyncSession = Depends(get_html_db)
):
    """Companies list page."""
    try:
        result = await list_companies(page=1, page_size=10, db=db, current_user=current_user)
        companies = [dict(item) for item in result.items]
    except Exception:
        # fallback to mock data
        companies = MOCK_COMPANIES
    
    context = {
        "request": request,
        "companies": companies,
        "current_user": current_user
    }
    return templates.TemplateResponse("companies/list.html", context)

@router.get("/companies/{company_id}", response_class=HTMLResponse)
async def company_detail(
    company_id: str,
    request: Request,
    current_user=CurrentActiveUser,
    db: AsyncSession = Depends(get_html_db)
):
    """Company detail page."""
    try:
        from app.schemas.company import Company as CompanySchema
        company = await get_company(int(company_id), db)
        company_data = CompanySchema.model_validate(company).dict()
    except Exception:
        # fallback to mock data
        company_data = {**MOCK_COMPANIES[0], "id": company_id}
    
    context = {
        "request": request,
        "company": company_data,
        "current_user": current_user
    }
    return templates.TemplateResponse("companies/detail.html", context)

@router.get("/companies/create", response_class=HTMLResponse)
async def company_create(
    request: Request,
    current_user=CurrentActiveUser
):
    """Company create page."""
    context = {
        "request": request,
        "current_user": current_user
    }
    return templates.TemplateResponse("companies/form.html", context)