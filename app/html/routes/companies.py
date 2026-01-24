from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi.templating import Jinja2Templates
import structlog
from app.models.user import User
from app.models.company import Company
from app.api.routes.companies import list_companies, get_company
from app.html.deps import get_html_db
from app.api.routes.auth import get_current_user_optional
from app.html.mock import MOCK_COMPANIES
from app.html.filters import datetime_format

router = APIRouter()
logger = structlog.get_logger()

templates = Jinja2Templates(directory="templates")
# Add datetime filter to templates
templates.env.filters["datetime_format"] = datetime_format


def _pydantic_to_dict(item):
    """Convert Pydantic model to dict, excluding _links field."""
    if hasattr(item, 'model_dump'):
        return item.model_dump(exclude={"_links"})
    return dict(item)


def _convert_data_for_template(data_dict):
    """Convert datetime and status fields for template rendering."""
    # Convert datetime to ISO string
    if "created_at" in data_dict and hasattr(data_dict["created_at"], "isoformat"):
        data_dict["created_at"] = data_dict["created_at"].isoformat()
    if "updated_at" in data_dict and hasattr(data_dict["updated_at"], "isoformat"):
        data_dict["updated_at"] = data_dict["updated_at"].isoformat()
    
    return data_dict

@router.get("/companies", response_class=HTMLResponse)
async def companies_list(
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db)
):
    """Companies list page with filtering and pagination."""
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Extract query parameters
    page = int(request.query_params.get('page', 1))
    page_size = int(request.query_params.get('page_size', 20))
    search = request.query_params.get('search', '')
    status_filter = request.query_params.get('status', '')
    
    try:
        # Get companies with filters
        result = await list_companies(
            page=page,
            page_size=page_size,
            search=search if search else None,
            status=status_filter if status_filter else None,
            db=db,
            current_user=current_user
        )
        
        companies = []
        for item in result.items:
            company_dict = _pydantic_to_dict(item)
            company_dict = _convert_data_for_template(company_dict)
            companies.append(company_dict)
        
        total_count = result.total
        total_pages = result.total_pages
        
    except Exception as e:
        logger.error("companies_list_error", error=str(e), exc_info=True)
        companies = []
        total_count = 0
        total_pages = 1
    
    context = {
        "request": request,
        "companies": companies,
        "current_user": current_user,
        "page": page,
        "page_size": page_size,
        "total_count": total_count,
        "total_pages": total_pages,
        "search": search,
        "status_filter": status_filter
    }
    
    return templates.TemplateResponse("companies/list.html", context)

@router.get("/companies/create", response_class=HTMLResponse)
async def company_create(
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db)
):
    """Company create page."""
    if not current_user:
        # Redirect to login page if user is not authenticated
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        # Redirect to login page if user is not active
        return RedirectResponse(url="/admin/login", status_code=303)
    
    context = {
        "request": request,
        "company": None,  # No company data for create form
        "current_user": current_user
    }
    return templates.TemplateResponse("companies/form.html", context)

@router.get("/companies/{company_id}", response_class=HTMLResponse)
async def company_detail(
    company_id: str,
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db)
):
    """Company detail page."""
    if not current_user:
        # Redirect to login page if user is not authenticated
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        # Redirect to login page if user is not active
        return RedirectResponse(url="/admin/login", status_code=303)
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

@router.get("/companies/{company_id}/edit", response_class=HTMLResponse)
async def company_edit(
    company_id: str,
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db)
):
    """Company edit page."""
    if not current_user:
        # Redirect to login page if user is not authenticated
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        # Redirect to login page if user is not active
        return RedirectResponse(url="/admin/login", status_code=303)
    
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
    return templates.TemplateResponse("companies/form.html", context)

@router.post("/companies", response_class=HTMLResponse)
async def company_create_post(
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db)
):
    """Handle company creation form submission."""
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Get form data
    form_data = await request.form()
    name = form_data.get("name", "").strip()
    contact_email = form_data.get("contact_email", "").strip()
    status = form_data.get("status", "active")
    
    if not name:
        # If validation fails, return to form with error
        context = {
            "request": request,
            "company": {"name": name, "contact_email": contact_email, "status": status},
            "current_user": current_user,
            "error": "Name is required field"
        }
        return templates.TemplateResponse("companies/form.html", context)
    
    try:
        # Create company via API
        from app.api.routes.companies import create_company
        from app.schemas.company_api import CompanyCreate
        
        company_create_data = CompanyCreate(
            name=name,
            contact_email=contact_email,
            status=status
        )
        
        created_company = await create_company(
            company_data=company_create_data,
            db=db,
            current_user=current_user
        )
        
        # Redirect to companies list after successful creation
        return RedirectResponse(url="/companies", status_code=303)
        
    except Exception as e:
        logger.error("company_create_error", error=str(e), exc_info=True)
        # If creation fails, return to form with error
        context = {
            "request": request,
            "company": {"name": name, "contact_email": contact_email, "status": status},
            "current_user": current_user,
            "error": f"Failed to create company: {str(e)}"
        }
        return templates.TemplateResponse("companies/form.html", context)


@router.delete("/companies/{company_id}")
async def company_delete(
    company_id: str,
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db)
):
    """Handle company deletion."""
    if not current_user:
        return JSONResponse(content={"error": "Unauthorized"}, status_code=401)
    
    if not current_user.is_active:
        return JSONResponse(content={"error": "Unauthorized"}, status_code=401)
    
    try:
        # Delete company via API
        from app.api.routes.companies import delete_company_general
        
        await delete_company_general(
            company_id=int(company_id),
            db=db,
            current_user=current_user
        )
        
        # Return success response
        return JSONResponse(content={"status": "deleted"}, status_code=200)
        
    except Exception as e:
        logger.error("company_delete_error", company_id=company_id, error=str(e), exc_info=True)
        # Return error response
        return JSONResponse(content={"error": f"Failed to delete company: {str(e)}"}, status_code=400)

@router.post("/companies/{company_id}", response_class=HTMLResponse)
async def company_update_post(
    company_id: str,
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db)
):
    """Handle company update form submission."""
    if not current_user:
        # Redirect to login page if user is not authenticated
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        # Redirect to login page if user is not active
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Get form data
    form_data = await request.form()
    name = form_data.get("name", "").strip()
    contact_email = form_data.get("contact_email", "").strip()
    status = form_data.get("status", "active")
    
    if not name:
        # If validation fails, return to form with error
        context = {
            "request": request,
            "company": {"id": company_id, "name": name, "contact_email": contact_email, "status": status},
            "current_user": current_user,
            "error": "Name is required field"
        }
        return templates.TemplateResponse("companies/form.html", context)
    
    try:
        # Update company via API
        from app.api.routes.companies import update_company
        from app.schemas.company_api import CompanyUpdate
        
        company_update_data = CompanyUpdate(
            name=name,
            contact_email=contact_email,
            status=status
        )
        
        updated_company = await update_company(
            company_id=int(company_id),
            company_data=company_update_data,
            db=db,
            current_user=current_user
        )
        
        # Redirect to companies list after successful update
        return RedirectResponse(url="/companies", status_code=303)
        
    except Exception as e:
        # If update fails, return to form with error
        context = {
            "request": request,
            "company": {"id": company_id, "name": name, "contact_email": contact_email, "status": status},
            "current_user": current_user,
            "error": f"Failed to update company: {str(e)}"
        }
        return templates.TemplateResponse("companies/form.html", context)