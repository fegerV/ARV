from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi.templating import Jinja2Templates
from app.models.user import User
from app.api.routes.ar_content import list_all_ar_content, get_ar_content_by_id, get_ar_viewer
from app.api.routes.analytics import analytics_content
from app.api.routes.companies import list_companies
from app.api.routes.projects import list_projects
from app.models.video import Video
from app.models.video_schedule import VideoSchedule as VideoScheduleModel
from app.services.video_scheduler import compute_video_status, compute_days_remaining, get_active_video
from app.services.marker_service import marker_service
from app.models.ar_content import ARContent
from app.utils.ar_content import build_public_url
from app.html.deps import get_html_db
from app.api.routes.auth import get_current_user_optional
from app.html.mock import MOCK_AR_CONTENT, AR_CONTENT_DETAIL_MOCK_DATA, PROJECT_CREATE_MOCK_DATA
from app.html.filters import datetime_format
from app.core.config import settings
import structlog
from datetime import datetime
from pathlib import Path

router = APIRouter()
logger = structlog.get_logger()

templates = Jinja2Templates(directory="templates")
# Add datetime filter to templates
templates.env.filters["datetime_format"] = datetime_format


def _serialize_datetime(value):
    """Serialize datetime to ISO 8601 string."""
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


async def _load_video_details(ar_content_id: int, db: AsyncSession) -> tuple[list[dict], dict | None]:
    """Load videos for AR content with schedules and active video details."""
    now = datetime.utcnow()
    stmt = select(Video).where(Video.ar_content_id == ar_content_id).order_by(Video.rotation_order.asc(), Video.id.asc())
    result = await db.execute(stmt)
    videos = list(result.scalars().all())

    schedule_map: dict[int, list[dict]] = {}
    if videos:
        video_ids = [video.id for video in videos]
        schedules_stmt = select(VideoScheduleModel).where(VideoScheduleModel.video_id.in_(video_ids))
        schedules_result = await db.execute(schedules_stmt)
        schedules = list(schedules_result.scalars().all())
        for schedule in schedules:
            schedule_map.setdefault(schedule.video_id, []).append({
                "id": schedule.id,
                "start_time": _serialize_datetime(schedule.start_time),
                "end_time": _serialize_datetime(schedule.end_time),
                "status": schedule.status,
                "description": schedule.description,
            })

    video_items = []
    for video in videos:
        schedules_summary = schedule_map.get(video.id, [])
        video_items.append({
            "id": video.id,
            "title": video.filename,
            "video_url": video.video_url,
            "preview_url": video.preview_url or video.video_url,
            "is_active": video.is_active,
            "rotation_type": video.rotation_type,
            "subscription_end": _serialize_datetime(video.subscription_end),
            "status": compute_video_status(video, now),
            "days_remaining": compute_days_remaining(video, now),
            "schedules_count": len(schedules_summary),
            "schedules_summary": schedules_summary,
        })

    active_video_info = None
    active_data = await get_active_video(ar_content_id, db)
    if active_data and active_data.get("video"):
        active_video = active_data["video"]
        active_schedule = None
        if active_data.get("schedule_id"):
            active_schedule = next(
                (item for item in schedule_map.get(active_video.id, []) if item.get("id") == active_data.get("schedule_id")),
                None
            )
        active_video_info = {
            "id": active_video.id,
            "title": active_video.filename,
            "video_url": active_video.video_url,
            "preview_url": active_video.preview_url or active_video.video_url,
            "source": active_data.get("source"),
            "expires_in": active_data.get("expires_in"),
            "schedule": active_schedule,
        }

    return video_items, active_video_info

@router.get("/ar-content", response_class=HTMLResponse)
async def ar_content_list(
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db)
):
    """AR Content list page."""
    if not current_user:
        # Redirect to login page if user is not authenticated
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        # Redirect to login page if user is not active
        return RedirectResponse(url="/admin/login", status_code=303)
    try:
        result = await list_all_ar_content(page=1, page_size=10, db=db)
        ar_content_list = [dict(item) for item in result.items]
        
        # Extract unique companies and statuses for filters
        unique_companies = list(set(item.get('company_name', '') for item in ar_content_list if item.get('company_name')))
        unique_statuses = list(set(item.get('status', '') for item in ar_content_list if item.get('status')))
    except Exception as exc:
        if not settings.DEBUG:
            logger.exception("ar_content_list_failed", error=str(exc))
            raise
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

@router.get("/ar-content/create", response_class=HTMLResponse)
async def ar_content_create(
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db)
):
    """AR Content create page."""
    if not current_user:
        # Redirect to login page if user is not authenticated
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        # Redirect to login page if user is not active
        return RedirectResponse(url="/admin/login", status_code=303)
    try:
        # Query companies and projects using the API routes to ensure proper access control
        from app.api.routes.companies import list_companies
        from app.api.routes.projects import list_projects
        
        # Get all companies and projects with proper access control
        # Pass only the required parameters to avoid Query object binding issues
        companies_result = await list_companies(
            page=1,
            page_size=100,
            search=None,
            status=None,
            db=db,
            current_user=current_user
        )
        companies = [dict(item) for item in companies_result.items]
        
        # Get all projects without filtering by company
        from sqlalchemy import select
        from app.models.project import Project
        from app.models.ar_content import ARContent
        from app.models.company import Company
        from sqlalchemy import func
        
        # Direct SQL query to get all projects
        query = select(Project).join(Company)
        result = await db.execute(query)
        all_projects = result.scalars().all()
        
        # Build projects data manually
        projects = []
        for project in all_projects:
            # Count AR content for this project
            ar_content_count_query = select(func.count()).select_from(ARContent).where(ARContent.project_id == project.id)
            ar_content_count_result = await db.execute(ar_content_count_query)
            ar_content_count = ar_content_count_result.scalar()
            
            project_dict = {
                "id": str(project.id),
                "name": project.name.replace('"', '"').replace("'", "&#x27;") if project.name else "",  # Защита от XSS и ошибок в JS
                "status": project.status,
                "company_id": project.company_id,
                "ar_content_count": ar_content_count,
                "created_at": project.created_at.isoformat() if hasattr(project.created_at, 'isoformat') else str(project.created_at) if project.created_at else None,
                "updated_at": project.updated_at.isoformat() if hasattr(project.updated_at, 'isoformat') else str(project.updated_at) if project.updated_at else None,
                "_links": {
                    "edit": f"/api/projects/{project.id}",
                    "delete": f"/api/projects/{project.id}",
                    "view_content": f"/api/projects/{project.id}/ar-content"
                }
            }
            projects.append(project_dict)
        
        # Create a mock result object similar to PaginatedProjectsResponse
        projects_result = type('MockResult', (), {
            'items': projects,
            'total': len(projects),
            'page': 1,
            'page_size': len(projects),
            'total_pages': 1
        })()
        
        if settings.DEBUG and not companies:
            data = PROJECT_CREATE_MOCK_DATA
        else:
            data = {
                "companies": companies,
                "projects": projects,
            }
    except Exception as exc:
        if not settings.DEBUG:
            logger.exception("ar_content_create_data_failed", error=str(exc))
            raise
        # fallback to mock data
        data = PROJECT_CREATE_MOCK_DATA
    
    # Create safe JavaScript versions of the data
    companies_js = [
        {
            "id": company.get("id"),
            "name": company.get("name"),
            "status": company.get("status"),
            "contact_email": company.get("contact_email"),
            "created_at": (company.get("created_at").isoformat() if company.get("created_at") and hasattr(company.get("created_at"), "isoformat")
                          else str(company.get("created_at")) if company.get("created_at") else None),
            "updated_at": (company.get("updated_at").isoformat() if company.get("updated_at") and hasattr(company.get("updated_at"), "isoformat")
                          else str(company.get("updated_at")) if company.get("updated_at") else None),
        }
        for company in data["companies"]
    ]
    
    projects_js = [
        {
            "id": project.get("id"),
            "name": project.get("name"),
            "company_id": project.get("company_id"),
            "status": project.get("status"),
            "description": project.get("description", ""),  # description может отсутствовать
            "created_at": (project.get("created_at").isoformat() if project.get("created_at") and hasattr(project.get("created_at"), "isoformat")
                          else str(project.get("created_at")) if project.get("created_at") else None),
            "updated_at": (project.get("updated_at").isoformat() if project.get("updated_at") and hasattr(project.get("updated_at"), "isoformat")
                          else str(project.get("updated_at")) if project.get("updated_at") else None),
        }
        for project in data["projects"]
    ]
    
    context = {
        "request": request,
        "companies": data["companies"],
        "projects": data["projects"],
        "companies_js": companies_js,
        "projects_js": projects_js,
        "current_user": current_user
    }
    return templates.TemplateResponse("ar-content/form.html", context)

@router.get("/ar-content/{ar_content_id}/edit", response_class=HTMLResponse)
async def ar_content_edit(
    ar_content_id: str,
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db)
):
    """AR Content edit page."""
    if not current_user:
        # Redirect to login page if user is not authenticated
        return RedirectResponse(url="/admin/login", status_code=303)

    if not current_user.is_active:
        # Redirect to login page if user is not active
        return RedirectResponse(url="/admin/login", status_code=303)

    try:
        # Get the AR content
        result = await get_ar_content_by_id_legacy(int(ar_content_id), db)

        # Convert to dict and handle datetime serialization
        if hasattr(result, "model_dump"):
            ar_content = result.model_dump()
        elif hasattr(result, "__dict__"):
            ar_content = result.__dict__
        else:
            ar_content = dict(result)

        # Convert datetime objects to strings for template and JSON serialization
        def convert_datetimes(obj):
            if isinstance(obj, dict):
                return {k: convert_datetimes(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert_datetimes(item) for item in obj]
            if hasattr(obj, "isoformat"):  # datetime objects
                return obj.isoformat()
            return obj

        ar_content = convert_datetimes(ar_content)

        # Get companies and projects
        companies_task = list_companies(
            page=1,
            page_size=100,
            search=None,
            status=None,
            db=db,
            current_user=current_user,
        )

        # Get all projects without filtering by company for edit form as well
        from sqlalchemy import select
        from app.models.project import Project
        from app.models.ar_content import ARContent
        from app.models.company import Company
        from sqlalchemy import func

        # Direct SQL query to get all projects
        query = select(Project).join(Company)
        result = await db.execute(query)
        all_projects = result.scalars().all()

        # Build projects data manually
        projects = []
        for project in all_projects:
            # Count AR content for this project
            ar_content_count_query = (
                select(func.count())
                .select_from(ARContent)
                .where(ARContent.project_id == project.id)
            )
            ar_content_count_result = await db.execute(ar_content_count_query)
            ar_content_count = ar_content_count_result.scalar()

            project_dict = {
                "id": str(project.id),
                "name": project.name.replace('"', '"').replace("'", "&#x27;")
                if project.name
                else "",  # Защита от XSS и ошибок в JS
                "status": project.status,
                "company_id": project.company_id,
                "ar_content_count": ar_content_count,
                "created_at": project.created_at.isoformat()
                if hasattr(project.created_at, "isoformat")
                else str(project.created_at)
                if project.created_at
                else None,
                "updated_at": project.updated_at.isoformat()
                if hasattr(project.updated_at, "isoformat")
                else str(project.updated_at)
                if project.updated_at
                else None,
                "_links": {
                    "edit": f"/api/projects/{project.id}",
                    "delete": f"/api/projects/{project.id}",
                    "view_content": f"/api/projects/{project.id}/ar-content",
                },
            }
            projects.append(project_dict)

        # Execute companies query
        companies_result = await companies_task
        companies = [dict(item) for item in companies_result.items]

        # Create safe JavaScript versions of the data
        companies_js = [
            {
                "id": company.get("id"),
                "name": company.get("name"),
                "status": company.get("status"),
                "contact_email": company.get("contact_email"),
                "created_at": (
                    company.get("created_at").isoformat()
                    if company.get("created_at")
                    and hasattr(company.get("created_at"), "isoformat")
                    else str(company.get("created_at"))
                    if company.get("created_at")
                    else None
                ),
                "updated_at": (
                    company.get("updated_at").isoformat()
                    if company.get("updated_at")
                    and hasattr(company.get("updated_at"), "isoformat")
                    else str(company.get("updated_at"))
                    if company.get("updated_at")
                    else None
                ),
            }
            for company in companies
        ]

        projects_js = [
            {
                "id": project.get("id"),
                "name": project.get("name"),
                "company_id": project.get("company_id"),
                "status": project.get("status"),
                "description": project.get("description", ""),  # description может отсутствовать
                "created_at": (
                    project.get("created_at").isoformat()
                    if project.get("created_at")
                    and hasattr(project.get("created_at"), "isoformat")
                    else str(project.get("created_at"))
                    if project.get("created_at")
                    else None
                ),
                "updated_at": (
                    project.get("updated_at").isoformat()
                    if project.get("updated_at")
                    and hasattr(project.get("updated_at"), "isoformat")
                    else str(project.get("updated_at"))
                    if project.get("updated_at")
                    else None
                ),
            }
            for project in projects
        ]
    except Exception as exc:
        if not settings.DEBUG:
            logger.exception("ar_content_edit_data_failed", error=str(exc))
            raise
        # fallback to mock data
        ar_content = {**AR_CONTENT_DETAIL_MOCK_DATA, "id": ar_content_id}
        companies = PROJECT_CREATE_MOCK_DATA["companies"]
        projects = PROJECT_CREATE_MOCK_DATA["projects"]

        # Create safe JavaScript versions of the mock data
        companies_js = [
            {
                "id": company.get("id"),
                "name": company.get("name"),
                "status": company.get("status"),
                "contact_email": company.get("contact_email"),
                "created_at": str(company.get("created_at"))
                if company.get("created_at")
                else None,
                "updated_at": str(company.get("updated_at"))
                if company.get("updated_at")
                else None,
            }
            for company in companies
        ]

        projects_js = [
            {
                "id": project.get("id"),
                "name": project.get("name"),
                "company_id": project.get("company_id"),
                "status": project.get("status"),
                "description": project.get("description", ""),  # description может отсутствовать
                "created_at": str(project.get("created_at"))
                if project.get("created_at")
                else None,
                "updated_at": str(project.get("updated_at"))
                if project.get("updated_at")
                else None,
            }
            for project in projects
        ]

    context = {
        "request": request,
        "ar_content": ar_content,
        "companies": companies,
        "projects": projects,
        "companies_js": companies_js,
        "projects_js": projects_js,
        "current_user": current_user,
    }
    return templates.TemplateResponse("ar-content/form.html", context)

@router.get("/ar-content/{ar_content_id}", response_class=HTMLResponse)
async def ar_content_detail(
    ar_content_id: str,
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db)
):
    """AR Content detail page."""
    if not current_user:
        # Redirect to login page if user is not authenticated
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        # Redirect to login page if user is not active
        return RedirectResponse(url="/admin/login", status_code=303)
    try:
        result = await get_ar_content_by_id(int(ar_content_id), db)
        
        # Convert to dict and handle datetime serialization
        if hasattr(result, "model_dump"):
            ar_content = result.model_dump()
        elif hasattr(result, "__dict__"):
            ar_content = result.__dict__
        else:
            ar_content = dict(result)
            
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

        try:
            views_30_days_result = await analytics_content(int(ar_content_id), db)
            views_30_days = int(views_30_days_result.get("views_30_days", 0))
        except Exception:
            views_30_days = 0

        ar_content["views_30_days"] = views_30_days
        ar_content["views_count"] = int(ar_content.get("views_count") or 0)
        if ar_content.get("thumbnail_url") is None and ar_content.get("photo_url"):
            ar_content["thumbnail_url"] = ar_content.get("photo_url")
        if ar_content.get("active_video") and not ar_content.get("active_video_title"):
            ar_content["active_video_title"] = ar_content["active_video"].get("title")

        videos, active_video_info = await _load_video_details(int(ar_content_id), db)
        if active_video_info and not ar_content.get("active_video_title"):
            ar_content["active_video_title"] = active_video_info.get("title")

        marker_metadata = ar_content.get("marker_metadata") or {}
        if ar_content.get("photo_path") and not marker_metadata.get("image_quality"):
            image_quality = marker_service.analyze_image_quality(ar_content.get("photo_path"))
            if image_quality:
                marker_metadata = {**marker_metadata, "image_quality": image_quality}
                try:
                    ar_content_row = await db.get(ARContent, int(ar_content_id))
                    if ar_content_row:
                        ar_content_row.marker_metadata = {
                            **(ar_content_row.marker_metadata or {}),
                            "image_quality": image_quality,
                        }
                        await db.commit()
                except Exception as exc:
                    await db.rollback()
                    logger.warning("marker_quality_persist_failed", error=str(exc))
        if not ar_content.get("marker_url") and ar_content.get("marker_path"):
            marker_path_value = ar_content.get("marker_path")
            marker_path = Path(marker_path_value)
            if not marker_path.is_absolute():
                marker_path = Path(settings.LOCAL_STORAGE_PATH) / marker_path_value
            ar_content["marker_url"] = build_public_url(marker_path)
        marker_metrics = {
            "file_size_kb": marker_metadata.get("file_size_kb"),
            "file_size_bytes": marker_metadata.get("file_size_bytes"),
            "generation_time_seconds": marker_metadata.get("generation_time_seconds"),
            "features_count": marker_metadata.get("features_count"),
            "features_density": marker_metadata.get("features_density"),
            "width": marker_metadata.get("width"),
            "height": marker_metadata.get("height"),
            "image_quality": marker_metadata.get("image_quality") or {},
        }
        
        debug_info = None
        if settings.DEBUG:
            debug_info = {
                "storage_path": ar_content.get("storage_path"),
                "photo_path": ar_content.get("photo_path"),
                "video_path": ar_content.get("video_path"),
                "qr_code_path": ar_content.get("qr_code_path"),
                "thumbnail_url": ar_content.get("thumbnail_url"),
                "marker_path": ar_content.get("marker_path"),
                "marker_url": ar_content.get("marker_url"),
                "marker_status": ar_content.get("marker_status"),
            }
        
        # Create a simplified version for JavaScript serialization
        ar_content_js = {
            "id": ar_content.get("id"),
            "company_id": ar_content.get("company_id"),
            "project_id": ar_content.get("project_id"),
            "order_number": ar_content.get("order_number"),
            "customer_name": ar_content.get("customer_name"),
            "customer_phone": ar_content.get("customer_phone"),
            "customer_email": ar_content.get("customer_email"),
            "duration_years": ar_content.get("duration_years"),
            "status": ar_content.get("status"),
            "photo_url": ar_content.get("photo_url"),
            "video_url": ar_content.get("video_url"),
            "thumbnail_url": ar_content.get("thumbnail_url"),
            "qr_code_url": ar_content.get("qr_code_url"),
            "marker_url": ar_content.get("marker_url"),
            "marker_status": ar_content.get("marker_status"),
            "marker_metadata": marker_metadata,
            "public_url": ar_content.get("public_url"),
            "unique_link": ar_content.get("unique_link"),
            "company_name": ar_content.get("company_name"),
            "project_name": ar_content.get("project_name"),
            "views_count": ar_content.get("views_count"),
            "views_30_days": ar_content.get("views_30_days"),
            "active_video_title": ar_content.get("active_video_title"),
            "created_at": ar_content.get("created_at").isoformat()
            if ar_content.get("created_at") and hasattr(ar_content.get("created_at"), "isoformat")
            else ar_content.get("created_at"),
            "updated_at": ar_content.get("updated_at").isoformat()
            if ar_content.get("updated_at") and hasattr(ar_content.get("updated_at"), "isoformat")
            else ar_content.get("updated_at"),
        }
        
    except Exception as exc:
        if not settings.DEBUG:
            logger.exception("ar_content_detail_failed", error=str(exc))
            raise
        # fallback to mock data
        ar_content = {**AR_CONTENT_DETAIL_MOCK_DATA, "id": ar_content_id}
        debug_info = None
        if settings.DEBUG:
            debug_info = {
                "storage_path": ar_content.get("storage_path"),
                "photo_path": ar_content.get("photo_path"),
                "video_path": ar_content.get("video_path"),
                "qr_code_path": ar_content.get("qr_code_path"),
                "thumbnail_url": ar_content.get("thumbnail_url"),
                "marker_path": ar_content.get("marker_path"),
                "marker_url": ar_content.get("marker_url"),
                "marker_status": ar_content.get("marker_status"),
            }
        videos, active_video_info = [], None
        marker_metadata = ar_content.get("marker_metadata") or {}
        marker_metrics = {
            "file_size_kb": marker_metadata.get("file_size_kb"),
            "file_size_bytes": marker_metadata.get("file_size_bytes"),
            "generation_time_seconds": marker_metadata.get("generation_time_seconds"),
            "features_count": marker_metadata.get("features_count"),
            "features_density": marker_metadata.get("features_density"),
            "width": marker_metadata.get("width"),
            "height": marker_metadata.get("height"),
            "image_quality": marker_metadata.get("image_quality") or {},
        }
        # Create a simplified version for JavaScript serialization from mock data
        ar_content_js = {
            'id': ar_content.get('id'),
            "company_id": ar_content.get("company_id"),
            "project_id": ar_content.get("project_id"),
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
            "marker_metadata": marker_metadata,
            'public_url': ar_content.get('public_url'),
            'unique_link': ar_content.get('unique_link'),
            'company_name': ar_content.get('company_name'),
            'project_name': ar_content.get('project_name'),
            'views_count': ar_content.get('views_count'),
            'views_30_days': ar_content.get('views_30_days'),
            'active_video_title': ar_content.get('active_video_title'),
            'created_at': ar_content.get('created_at').isoformat() if ar_content.get('created_at') and hasattr(ar_content.get('created_at'), 'isoformat') else ar_content.get('created_at'),
            'updated_at': ar_content.get('updated_at').isoformat() if ar_content.get('updated_at') and hasattr(ar_content.get('updated_at'), 'isoformat') else ar_content.get('updated_at')
        }
    
    context = {
        "request": request,
        "ar_content": ar_content,
        "ar_content_js": ar_content_js,
        "videos_js": videos,
        "active_video_js": active_video_info,
        "marker_metrics": marker_metrics,
        "debug_info": debug_info,
        "current_user": current_user
    }
    return templates.TemplateResponse("ar-content/detail.html", context)


@router.get("/view/{unique_id}", response_class=HTMLResponse)
async def ar_content_viewer(
    unique_id: str,
    db: AsyncSession = Depends(get_html_db)
):
    """Public AR viewer page."""
    return await get_ar_viewer(unique_id, db)
