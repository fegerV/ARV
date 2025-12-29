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
    """Projects list page."""
    if not current_user:
        # Redirect to login page if user is not authenticated
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        # Redirect to login page if user is not active
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Get query parameters for filtering and pagination
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 10))
        status_filter = request.query_params.get("status", "")
        company_filter = request.query_params.get("company", "")
        search_filter = request.query_params.get("search", "")
        
        # Prepare filter parameters for API
        company_id_filter = int(company_filter) if company_filter and company_filter.isdigit() else None
        
        # Get projects from API with filters
        result = await list_projects(
            page=page,
            page_size=page_size,
            company_id=company_id_filter,
            db=db,
            current_user=current_user
        )
        projects = [dict(item) for item in result.items]
        
        # Get company names and AR content count for each project
        from app.api.routes.companies import get_company
        from app.models.ar_content import ARContent
        from sqlalchemy import select
        
        for project in projects:
            try:
                company = await get_company(int(project["company_id"]), db)
                project["company_name"] = company.name
            except Exception:
                project["company_name"] = "Unknown Company"
            
            try:
                # Get AR content count for the project
                from sqlalchemy import select
                ar_content_count_query = select(func.count()).select_from(ARContent).where(ARContent.project_id == int(project["id"]))
                ar_content_count_result = await db.execute(ar_content_count_query)
                ar_content_count = ar_content_count_result.scalar()
                project["ar_content_count"] = ar_content_count or 0
            except Exception:
                project["ar_content_count"] = 0
    except Exception as e:
        # Log the error for debugging
        print(f"Error in projects_list: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # For any error, return an empty list instead of mock data
        # This prevents showing potentially outdated mock data when real data should be shown
        projects = []
        # Also make sure total_count and total_pages are set appropriately
        total_count = 0
        total_pages = 0
    
    # Get companies for filter dropdown
    try:
        from app.api.routes.companies import list_companies
        companies_result = await list_companies(page=1, page_size=100, db=db, current_user=current_user)
        companies = [dict(item) for item in companies_result.items]
    except Exception:
        # fallback to mock data
        companies = PROJECT_CREATE_MOCK_DATA["companies"]
    
    # Calculate total pages
    total_count = result.total if 'result' in locals() else len(projects)
    total_pages = result.total_pages if 'result' in locals() else 1
    
    context = {
        "request": request,
        "projects": projects,
        "companies": companies,
        "current_user": current_user,
        "page": page,
        "page_size": page_size,
        "total_count": total_count,
        "total_pages": total_pages
    }
    
    # Handle the case where there was an exception and result is not defined
    if 'result' not in locals():
        context["total_count"] = len(projects)
        context["total_pages"] = 1
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
    except Exception:
        # fallback to mock data
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
    except Exception:
        # fallback to mock data
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
    except Exception:
        # fallback to mock data
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