from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from fastapi.templating import Jinja2Templates
from app.models.user import User
from app.models.ar_content import ARContent
from app.api.routes.projects import list_projects, get_project
from app.html.deps import get_html_db
from app.api.routes.auth import get_current_user_optional
from app.html.mock import MOCK_PROJECTS, PROJECT_CREATE_MOCK_DATA
from app.html.filters import datetime_format

router = APIRouter()

templates = Jinja2Templates(directory="templates")
# Add datetime filter to templates
templates.env.filters["datetime_format"] = datetime_format

@router.get("/projects", response_class=HTMLResponse)
async def projects_list(
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db)
):
    """Projects list page with filtering and pagination."""
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Get query parameters
    page = int(request.query_params.get("page", 1))
    page_size = int(request.query_params.get("page_size", 20))
    company_filter = request.query_params.get("company", "")
    status_filter = request.query_params.get("status", "")
    
    # Convert filters to appropriate types
    company_id_filter = int(company_filter) if company_filter and company_filter.isdigit() else None
    
    try:
        # Get projects with filters
        result = await list_projects(
            page=page,
            page_size=page_size,
            company_id=company_id_filter,
            db=db,
            current_user=current_user
        )
        
        projects = []
        from app.models.company import Company
        from sqlalchemy import select
        
        for item in result.items:
            project_dict = dict(item)
            
            # Get company name
            try:
                company = await db.get(Company, project_dict["company_id"])
                project_dict["company_name"] = company.name if company else "Unknown"
            except Exception:
                project_dict["company_name"] = "Unknown"
            
            # Apply status filter if specified
            if status_filter and project_dict.get("status") != status_filter:
                continue
            
            projects.append(project_dict)
        
        total_count = result.total
        total_pages = result.total_pages
        
    except Exception as e:
        import structlog
        logger = structlog.get_logger()
        logger.error("projects_list_error", error=str(e))
        projects = []
        total_count = 0
        total_pages = 1
    
    # Get companies for filter dropdown
    try:
        from app.models.company import Company
        from sqlalchemy import select
        
        companies_query = select(Company).order_by(Company.name)
        companies_result = await db.execute(companies_query)
        companies = [
            {"id": c.id, "name": c.name}
            for c in companies_result.scalars().all()
        ]
    except Exception as e:
        import structlog
        logger = structlog.get_logger()
        logger.error("companies_fetch_error", error=str(e))
        companies = []
    
    context = {
        "request": request,
        "projects": projects,
        "companies": companies,
        "current_user": current_user,
        "page": page,
        "page_size": page_size,
        "total_count": total_count,
        "total_pages": total_pages,
        "company_filter": company_filter,
        "status_filter": status_filter
    }
    
    return templates.TemplateResponse("projects/list.html", context)

@router.get("/projects/create", response_class=HTMLResponse)
async def project_create(
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db)
):
    """Project create page."""
    if not current_user:
        # Redirect to login page if user is not authenticated
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        # Redirect to login page if user is not active
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        from app.api.routes.companies import list_companies
        companies_result = await list_companies(page=1, page_size=100, db=db, current_user=current_user)
        companies = [dict(item) for item in companies_result.items]
    except Exception as e:
        # Log error and try direct database query as fallback
        print(f"Error fetching companies via API: {e}")
        try:
            from sqlalchemy import select
            from app.models.company import Company
            
            companies_query = select(Company)
            companies_result = await db.execute(companies_query)
            companies = []
            for company in companies_result.scalars().all():
                companies.append({
                    "id": company.id,
                    "name": company.name,
                    "contact_email": company.contact_email,
                    "status": company.status,
                    "created_at": company.created_at,
                    "updated_at": company.updated_at
                })
        except Exception as db_error:
            print(f"Error fetching companies from database: {db_error}")
            # fallback to mock data only as last resort
            companies = PROJECT_CREATE_MOCK_DATA["companies"]
    
    context = {
        "request": request,
        "companies": companies,
        "current_user": current_user,
        "project": None  # Explicitly set project to None for create form
    }
    return templates.TemplateResponse("projects/form.html", context)

@router.get("/projects/{project_id}", response_class=HTMLResponse)
async def project_detail(
    project_id: str,
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db)
):
    """Project detail page."""
    if not current_user:
        # Redirect to login page if user is not authenticated
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        # Redirect to login page if user is not active
        return RedirectResponse(url="/admin/login", status_code=303)
    try:
        project = await get_project(int(project_id), db)
        project_data = dict(project)
    except Exception:
        # fallback to mock data
        project_data = {**MOCK_PROJECTS[0], "id": project_id}
    
    # Get companies for edit form
    try:
        from app.api.routes.companies import list_companies
        companies_result = await list_companies(page=1, page_size=100, db=db, current_user=current_user)
        companies = [dict(item) for item in companies_result.items]
    except Exception as e:
        # Log error and try direct database query as fallback
        print(f"Error fetching companies via API: {e}")
        try:
            from sqlalchemy import select
            from app.models.company import Company
            
            companies_query = select(Company)
            companies_result = await db.execute(companies_query)
            companies = []
            for company in companies_result.scalars().all():
                companies.append({
                    "id": company.id,
                    "name": company.name,
                    "contact_email": company.contact_email,
                    "status": company.status,
                    "created_at": company.created_at,
                    "updated_at": company.updated_at
                })
        except Exception as db_error:
            print(f"Error fetching companies from database: {db_error}")
            # fallback to mock data only as last resort
            companies = PROJECT_CREATE_MOCK_DATA["companies"]
    
    context = {
        "request": request,
        "project": project_data,
        "current_user": current_user,
        "companies": companies
    }
    return templates.TemplateResponse("projects/form.html", context)

@router.get("/projects/{project_id}/edit", response_class=HTMLResponse)
async def project_edit(
    project_id: str,
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db)
):
    """Project edit page."""
    if not current_user:
        # Redirect to login page if user is not authenticated
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        # Redirect to login page if user is not active
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        project = await get_project(int(project_id), db)
        project_data = dict(project)
    except Exception:
        # fallback to mock data
        project_data = {**MOCK_PROJECTS[0], "id": project_id}
    
    # Get companies for edit form
    try:
        from app.api.routes.companies import list_companies
        companies_result = await list_companies(page=1, page_size=100, db=db, current_user=current_user)
        companies = [dict(item) for item in companies_result.items]
    except Exception as e:
        # Log error and try direct database query as fallback
        print(f"Error fetching companies via API: {e}")
        try:
            from sqlalchemy import select
            from app.models.company import Company
            
            companies_query = select(Company)
            companies_result = await db.execute(companies_query)
            companies = []
            for company in companies_result.scalars().all():
                companies.append({
                    "id": company.id,
                    "name": company.name,
                    "contact_email": company.contact_email,
                    "status": company.status,
                    "created_at": company.created_at,
                    "updated_at": company.updated_at
                })
        except Exception as db_error:
            print(f"Error fetching companies from database: {db_error}")
            # fallback to mock data only as last resort
            companies = PROJECT_CREATE_MOCK_DATA["companies"]
    
    context = {
        "request": request,
        "project": project_data,
        "companies": companies,
        "current_user": current_user
    }
    return templates.TemplateResponse("projects/form.html", context)

@router.post("/projects", response_class=HTMLResponse)
async def project_create_post(
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db)
):
    """Handle project creation form submission."""
    if not current_user:
        # Redirect to login page if user is not authenticated
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        # Redirect to login page if user is not active
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Get form data
    form_data = await request.form()
    name = form_data.get("name", "").strip()
    company_id = form_data.get("company_id")
    status = form_data.get("status", "active")
    description = form_data.get("description", "").strip()
    
    if not name or not company_id:
        # If validation fails, return to form with error
        try:
            from app.api.routes.companies import list_companies
            companies_result = await list_companies(page=1, page_size=100, db=db, current_user=current_user)
            companies = [dict(item) for item in companies_result.items]
        except Exception:
            companies = PROJECT_CREATE_MOCK_DATA["companies"]
        
        context = {
            "request": request,
            "companies": companies,
            "current_user": current_user,
            "error": "Name and Company are required fields"
        }
        return templates.TemplateResponse("projects/form.html", context)
    
    try:
        # Create project via API
        from app.api.routes.projects import create_project_general
        from app.schemas.project_api import ProjectCreate
        
        project_create_data = ProjectCreate(
            name=name,
            company_id=int(company_id),
            status=status,
            description=description
        )
        
        created_project = await create_project_general(
            project_data=project_create_data,
            db=db,
            current_user=current_user
        )
        
        # Redirect to projects list after successful creation
        return RedirectResponse(url="/projects", status_code=303)
        
    except Exception as e:
        # If creation fails, return to form with error
        try:
            from app.api.routes.companies import list_companies
            companies_result = await list_companies(page=1, page_size=100, db=db, current_user=current_user)
            companies = [dict(item) for item in companies_result.items]
        except Exception:
            companies = PROJECT_CREATE_MOCK_DATA["companies"]
        
        context = {
            "request": request,
            "companies": companies,
            "current_user": current_user,
            "error": f"Failed to create project: {str(e)}"
        }
        return templates.TemplateResponse("projects/form.html", context)

@router.post("/projects/{project_id}", response_class=HTMLResponse)
async def project_update_post(
    project_id: str,
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db)
):
    """Handle project update form submission."""
    if not current_user:
        # Redirect to login page if user is not authenticated
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        # Redirect to login page if user is not active
        return RedirectResponse(url="/admin/login", status_code=303)
    
    # Get form data
    form_data = await request.form()
    name = form_data.get("name", "").strip()
    company_id = form_data.get("company_id")
    status = form_data.get("status", "active")
    description = form_data.get("description", "").strip()
    
    if not name or not company_id:
        # If validation fails, return to form with error
        try:
            from app.api.routes.companies import list_companies
            companies_result = await list_companies(page=1, page_size=100, db=db, current_user=current_user)
            companies = [dict(item) for item in companies_result.items]
        except Exception:
            companies = PROJECT_CREATE_MOCK_DATA["companies"]
        
        context = {
            "request": request,
            "companies": companies,
            "current_user": current_user,
            "project": {"id": project_id, "name": name, "company_id": company_id, "status": status, "description": description},
            "error": "Name and Company are required fields"
        }
        return templates.TemplateResponse("projects/form.html", context)
    
    try:
        # Update project via API
        from app.api.routes.projects import update_project_general
        from app.schemas.project_api import ProjectUpdate
        
        project_update_data = ProjectUpdate(
            name=name,
            company_id=int(company_id),
            status=status,
            description=description
        )
        
        updated_project = await update_project_general(
            project_id=int(project_id),
            project_data=project_update_data,
            db=db,
            current_user=current_user
        )
        
        # Redirect to projects list after successful update
        return RedirectResponse(url="/projects", status_code=303)
        
    except Exception as e:
        # If update fails, return to form with error
        try:
            from app.api.routes.companies import list_companies
            companies_result = await list_companies(page=1, page_size=100, db=db, current_user=current_user)
            companies = [dict(item) for item in companies_result.items]
        except Exception:
            companies = PROJECT_CREATE_MOCK_DATA["companies"]
        
        context = {
            "request": request,
            "companies": companies,
            "current_user": current_user,
            "project": {"id": project_id, "name": name, "company_id": company_id, "status": status, "description": description},
            "error": f"Failed to update project: {str(e)}"
        }
        return templates.TemplateResponse("projects/form.html", context)

@router.delete("/projects/{project_id}")
async def project_delete(
    project_id: str,
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db)
):
    """Handle project deletion."""
    if not current_user:
        # Return 401 if user is not authenticated
        from fastapi.responses import JSONResponse
        return JSONResponse(content={"error": "Unauthorized"}, status_code=401)
    
    if not current_user.is_active:
        # Return 401 if user is not active
        from fastapi.responses import JSONResponse
        return JSONResponse(content={"error": "Unauthorized"}, status_code=401)
    
    try:
        # Delete project via API
        from app.api.routes.projects import delete_project_general
        
        await delete_project_general(
            project_id=int(project_id),
            db=db,
            current_user=current_user
        )
        
        # Return success response for JavaScript
        from fastapi.responses import JSONResponse
        return JSONResponse(content={"status": "deleted"}, status_code=200)
        
    except Exception as e:
        # Return error response for JavaScript
        from fastapi.responses import JSONResponse
        return JSONResponse(content={"error": f"Failed to delete project: {str(e)}"}, status_code=400)