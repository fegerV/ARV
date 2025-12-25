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
        print(f"🔍 Result type: {type(result)}")
        print(f"🔍 Result has model_dump: {hasattr(result, 'model_dump')}")
        
        # Convert to dict and handle datetime serialization
        if hasattr(result, 'model_dump'):
            ar_content = result.model_dump()
        elif hasattr(result, '__dict__'):
            ar_content = result.__dict__
        else:
            ar_content = dict(result)
            
        print(f"🔍 ar_content type: {type(ar_content)}")
        print(f"🔍 ar_content keys: {list(ar_content.keys()) if isinstance(ar_content, dict) else 'Not a dict'}")
        
        # Convert datetime objects to strings for template and JSON serialization
        def convert_datetimes(obj):
            if isinstance(obj, dict):
                return {k: convert_datetimes(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_datetimes(item) for item in obj]
            elif hasattr(obj, 'isoformat'):  # datetime objects
                return obj.isoformat()
            else:
                return obj
        
        ar_content = convert_datetimes(ar_content)
        
        # Create a simplified version for JavaScript serialization
        ar_content_js = {
            'id': ar_content.get('id'),
            'order_number': ar_content.get('order_number'),
            'customer_name': ar_content.get('customer_name'),
            'customer_phone': ar_content.get('customer_phone'),
            'customer_email': ar_content.get('customer_email'),
            'duration_years': ar_content.get('duration_years'),
            'status': ar_content.get('status'),
            'photo_url': ar_content.get('photo_url'),
            'video_url': ar_content.get('video_url'),
            'thumbnail_url': ar_content.get('thumbnail_url'),
            'qr_code_url': ar_content.get('qr_code_url'),
            'marker_url': ar_content.get('marker_url'),
            'marker_status': ar_content.get('marker_status'),
            'public_url': ar_content.get('public_url'),
            'unique_link': ar_content.get('unique_link'),
            'company_name': ar_content.get('company_name'),
            'project_name': ar_content.get('project_name'),
            'views_count': ar_content.get('views_count'),
            'views_30_days': ar_content.get('views_30_days'),
            'active_video_title': ar_content.get('active_video_title'),
            'created_at': ar_content.get('created_at'),
            'updated_at': ar_content.get('updated_at')
        }
        
        # Debug: check for any remaining datetime objects
        def find_datetimes(obj, path=""):
            if hasattr(obj, 'isoformat'):
                print(f"⚠️  Found datetime at {path}: {type(obj)}")
                return True
            elif isinstance(obj, dict):
                found = False
                for k, v in obj.items():
                    if find_datetimes(v, f"{path}.{k}" if path else k):
                        found = True
                return found
            elif isinstance(obj, list):
                found = False
                for i, v in enumerate(obj):
                    if find_datetimes(v, f"{path}[{i}]" if path else f"[{i}]"):
                        found = True
                return found
            return False
        
        print("🔍 Checking for datetime objects in ar_content...")
        find_datetimes(ar_content)
        print("✅ DateTime check complete")
    except Exception:
        # fallback to mock data
        ar_content = {**AR_CONTENT_DETAIL_MOCK_DATA, "id": ar_content_id}
        # Create a simplified version for JavaScript serialization from mock data
        ar_content_js = {
            'id': ar_content.get('id'),
            'order_number': ar_content.get('order_number'),
            'customer_name': ar_content.get('customer_name'),
            'customer_phone': ar_content.get('customer_phone'),
            'customer_email': ar_content.get('customer_email'),
            'duration_years': ar_content.get('duration_years'),
            'status': ar_content.get('status'),
            'photo_url': ar_content.get('photo_url'),
            'video_url': ar_content.get('video_url'),
            'thumbnail_url': ar_content.get('thumbnail_url'),
            'qr_code_url': ar_content.get('qr_code_url'),
            'marker_url': ar_content.get('marker_url'),
            'marker_status': ar_content.get('marker_status'),
            'public_url': ar_content.get('public_url'),
            'unique_link': ar_content.get('unique_link'),
            'company_name': ar_content.get('company_name'),
            'project_name': ar_content.get('project_name'),
            'views_count': ar_content.get('views_count'),
            'views_30_days': ar_content.get('views_30_days'),
            'active_video_title': ar_content.get('active_video_title'),
            'created_at': ar_content.get('created_at'),
            'updated_at': ar_content.get('updated_at')
        }
    
    context = {
        "request": request,
        "ar_content": ar_content,
        "ar_content_js": ar_content_js,
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
