from fastapi import APIRouter, Request, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi.templating import Jinja2Templates
from app.models.user import User
from app.api.routes.ar_content import (
    list_all_ar_content, 
    get_ar_content_by_id, 
    get_ar_viewer,
    get_ar_content_by_id_legacy,
    _create_ar_content,
    update_ar_content,
    delete_ar_content_by_id
)
from app.schemas.ar_content import ARContentUpdate
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

logger = structlog.get_logger()

router = APIRouter()

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
    # Get pagination parameters from query string
    page = int(request.query_params.get("page", 1))
    page_size = int(request.query_params.get("page_size", 20))
    
    # Validate page_size - only allow 20, 30, 40, 50
    if page_size not in [20, 30, 40, 50]:
        page_size = 20
    
    try:
        result = await list_all_ar_content(page=page, page_size=page_size, db=db)
        ar_content_list = []
        
        # Recalculate URLs for each item based on current path structure
        # Load all AR content models in one query to avoid N+1 problem
        ar_content_ids = [item.id for item in result.items]
        ar_content_models = {}
        if ar_content_ids:
            from sqlalchemy.orm import selectinload
            stmt = select(ARContent).options(
                selectinload(ARContent.company),
                selectinload(ARContent.project)
            ).where(ARContent.id.in_(ar_content_ids))
            models_result = await db.execute(stmt)
            for model in models_result.scalars().all():
                ar_content_models[model.id] = model
        
        for item in result.items:
            item_dict = dict(item)
            
            # Recalculate URLs from paths if they exist
            from app.utils.ar_content import get_ar_content_storage_path
            
            # Get the AR content model from preloaded dict
            ar_content_model = ar_content_models.get(item_dict.get('id'))
            
            if ar_content_model:
                # Recalculate URLs from paths - use build_public_url without file existence checks
                # This is much faster than checking Path.exists() for each file
                
                # Recalculate photo_url from photo_path
                if ar_content_model.photo_path and not item_dict.get('photo_url'):
                    try:
                        photo_path = Path(ar_content_model.photo_path)
                        if photo_path.is_absolute():
                            item_dict['photo_url'] = build_public_url(photo_path)
                        else:
                            # Relative path - build absolute
                            photo_path_abs = Path(settings.STORAGE_BASE_PATH) / photo_path
                            item_dict['photo_url'] = build_public_url(photo_path_abs)
                    except Exception as e:
                        logger.warning("photo_url_recalc_failed", error=str(e), ar_content_id=item_dict.get('id'))
                
                # Recalculate video_url from video_path
                if ar_content_model.video_path and not item_dict.get('video_url'):
                    try:
                        video_path = Path(ar_content_model.video_path)
                        if video_path.is_absolute():
                            item_dict['video_url'] = build_public_url(video_path)
                        else:
                            video_path_abs = Path(settings.STORAGE_BASE_PATH) / video_path
                            item_dict['video_url'] = build_public_url(video_path_abs)
                    except Exception as e:
                        logger.warning("video_url_recalc_failed", error=str(e), ar_content_id=item_dict.get('id'))
                
                # Recalculate qr_code_url from qr_code_path
                if ar_content_model.qr_code_path and not item_dict.get('qr_code_url'):
                    try:
                        qr_path = Path(ar_content_model.qr_code_path)
                        if qr_path.is_absolute():
                            item_dict['qr_code_url'] = build_public_url(qr_path)
                        else:
                            qr_path_abs = Path(settings.STORAGE_BASE_PATH) / qr_path
                            item_dict['qr_code_url'] = build_public_url(qr_path_abs)
                    except Exception as e:
                        logger.warning("qr_code_url_recalc_failed", error=str(e), ar_content_id=item_dict.get('id'))
                
                # Recalculate thumbnail_url - use photo directory or new structure
                if not item_dict.get('thumbnail_url'):
                    try:
                        if ar_content_model.photo_path:
                            photo_path = Path(ar_content_model.photo_path)
                            if photo_path.is_absolute():
                                thumbnail_path = photo_path.parent / "thumbnail.webp"
                            else:
                                photo_path_abs = Path(settings.STORAGE_BASE_PATH) / photo_path
                                thumbnail_path = photo_path_abs.parent / "thumbnail.webp"
                            item_dict['thumbnail_url'] = build_public_url(thumbnail_path)
                        elif item_dict.get('photo_url'):
                            # Fallback to photo_url if no photo_path
                            item_dict['thumbnail_url'] = item_dict['photo_url']
                    except Exception as e:
                        logger.warning("thumbnail_url_recalc_failed", error=str(e), ar_content_id=item_dict.get('id'))
                        # Final fallback
                        if not item_dict.get('thumbnail_url') and item_dict.get('photo_url'):
                            item_dict['thumbnail_url'] = item_dict['photo_url']
            
            ar_content_list.append(item_dict)
        
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
        total_count = len(ar_content_list)
        total_pages = 1
    else:
        total_count = result.total
        total_pages = result.total_pages
    
    context = {
        "request": request,
        "ar_content_list": ar_content_list,
        "unique_companies": unique_companies,
        "unique_statuses": unique_statuses,
        "page": page,
        "page_size": page_size,
        "total_count": total_count,
        "total_pages": total_pages,
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

@router.delete("/ar-content/{ar_content_id}")
async def ar_content_delete(
    ar_content_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db)
):
    """Handle AR content deletion."""
    if not current_user:
        return JSONResponse(content={"error": "Unauthorized"}, status_code=401)
    
    if not current_user.is_active:
        return JSONResponse(content={"error": "Unauthorized"}, status_code=401)
    
    try:
        # Call API to delete AR content
        # Use injected BackgroundTasks from FastAPI
        result = await delete_ar_content_by_id(
            content_id=int(ar_content_id),
            background_tasks=background_tasks,
            db=db
        )
        
        logger.info("ar_content_deleted", ar_content_id=ar_content_id)
        return JSONResponse(content={"status": "deleted"}, status_code=200)
        
    except Exception as e:
        logger.error("ar_content_delete_error", ar_content_id=ar_content_id, error=str(e), exc_info=True)
        error_message = str(e)
        status_code = 500
        
        # Extract more detailed error message if available
        if hasattr(e, 'detail'):
            error_message = e.detail
            if hasattr(e, 'status_code'):
                status_code = e.status_code
        elif hasattr(e, 'args') and len(e.args) > 0:
            error_message = str(e.args[0])
        
        # Check for specific error types
        if "not found" in error_message.lower() or "404" in str(e):
            status_code = 404
        elif "unauthorized" in error_message.lower() or "401" in str(e):
            status_code = 401
        
        return JSONResponse(
            content={"error": f"Failed to delete AR content: {error_message}"}, 
            status_code=status_code
        )


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
            "is_valid": marker_metadata.get("is_valid", None),
            "validation_warnings": marker_metadata.get("validation_warnings", []),
        }
        
        # Recalculate storage_path - use existing path from DB if available, otherwise build new
        storage_path = None
        try:
            ar_content_model = await db.get(ARContent, int(ar_content_id))
            if ar_content_model:
                # If photo_path exists, try to extract storage_path from it
                if ar_content_model.photo_path:
                    photo_path = Path(ar_content_model.photo_path)
                    if photo_path.is_absolute() and photo_path.exists():
                        # Use parent directory of photo as storage_path
                        storage_path = photo_path.parent
                    elif photo_path.is_absolute():
                        # File doesn't exist, but use parent directory anyway
                        storage_path = photo_path.parent
                    else:
                        # Relative path - try to build from STORAGE_BASE_PATH
                        photo_path_abs = Path(settings.STORAGE_BASE_PATH) / photo_path
                        if photo_path_abs.exists():
                            storage_path = photo_path_abs.parent
                        else:
                            storage_path = photo_path_abs.parent
                
                # If still no storage_path, build new one
                if not storage_path:
                    from app.utils.ar_content import get_ar_content_storage_path
                    storage_path = await get_ar_content_storage_path(ar_content_model, db)
                
                ar_content["storage_path"] = str(storage_path)
        except Exception as e:
            logger.warning("storage_path_recalc_failed", error=str(e), ar_content_id=ar_content_id)
        
        # Recalculate URLs from paths - use build_public_url without file existence checks
        # This is much faster and avoids issues with file location mismatches
        if ar_content.get("photo_path") and not ar_content.get("photo_url"):
            try:
                photo_path = Path(ar_content["photo_path"])
                if photo_path.is_absolute():
                    ar_content["photo_url"] = build_public_url(photo_path)
                else:
                    # Relative path - build absolute
                    photo_path_abs = Path(settings.STORAGE_BASE_PATH) / photo_path
                    ar_content["photo_url"] = build_public_url(photo_path_abs)
            except Exception as e:
                logger.warning("photo_url_recalc_failed", error=str(e), ar_content_id=ar_content_id)
        
        if ar_content.get("video_path") and not ar_content.get("video_url"):
            try:
                video_path = Path(ar_content["video_path"])
                if video_path.is_absolute():
                    ar_content["video_url"] = build_public_url(video_path)
                else:
                    video_path_abs = Path(settings.STORAGE_BASE_PATH) / video_path
                    ar_content["video_url"] = build_public_url(video_path_abs)
            except Exception as e:
                logger.warning("video_url_recalc_failed", error=str(e), ar_content_id=ar_content_id)
        
        if ar_content.get("qr_code_path") and not ar_content.get("qr_code_url"):
            try:
                qr_path = Path(ar_content["qr_code_path"])
                if qr_path.is_absolute():
                    ar_content["qr_code_url"] = build_public_url(qr_path)
                else:
                    qr_path_abs = Path(settings.STORAGE_BASE_PATH) / qr_path
                    ar_content["qr_code_url"] = build_public_url(qr_path_abs)
            except Exception as e:
                logger.warning("qr_code_url_recalc_failed", error=str(e), ar_content_id=ar_content_id)
        
        # Recalculate thumbnail_url - use photo directory from DB path
        if not ar_content.get("thumbnail_url"):
            try:
                if ar_content.get("photo_path"):
                    # Use photo directory from DB path (preserves old structure)
                    photo_path = Path(ar_content["photo_path"])
                    if photo_path.is_absolute():
                        thumbnail_path = photo_path.parent / "thumbnail.webp"
                    else:
                        # Relative path - try to build absolute
                        photo_path_abs = Path(settings.STORAGE_BASE_PATH) / photo_path
                        thumbnail_path = photo_path_abs.parent / "thumbnail.webp"
                    ar_content["thumbnail_url"] = build_public_url(thumbnail_path)
                elif storage_path:
                    # Fallback: use storage_path from new structure
                    thumbnail_path = storage_path / "thumbnail.webp"
                    ar_content["thumbnail_url"] = build_public_url(thumbnail_path)
                elif ar_content.get("photo_url"):
                    # Final fallback to photo_url
                    ar_content["thumbnail_url"] = ar_content["photo_url"]
            except Exception as e:
                logger.warning("thumbnail_url_recalc_failed", error=str(e), ar_content_id=ar_content_id)
                # Final fallback
                if ar_content.get("photo_url"):
                    ar_content["thumbnail_url"] = ar_content["photo_url"]
        
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
            "storage_path": ar_content.get("storage_path"),
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
            "is_valid": marker_metadata.get("is_valid", None),
            "validation_warnings": marker_metadata.get("validation_warnings", []),
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


@router.post("/ar-content", response_class=HTMLResponse)
async def ar_content_create_post(
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db)
):
    """Handle AR content creation form submission."""
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Get form data
        form_data = await request.form()
        company_id = int(form_data.get("company_id", 0))
        project_id = int(form_data.get("project_id", 0))
        customer_name = form_data.get("customer_name", "").strip()
        customer_phone = form_data.get("customer_phone", "").strip()
        customer_email = form_data.get("customer_email", "").strip()
        duration_years = int(form_data.get("duration_years", 1))
        
        # Get files from form
        photo_file = form_data.get("photo_file")
        video_file = form_data.get("video_file")
        
        # Validation
        if not company_id or not project_id:
            raise ValueError("Company and Project are required")
        if not customer_name:
            raise ValueError("Customer name is required")
        if duration_years not in [1, 3, 5]:
            raise ValueError("Duration must be 1, 3, or 5 years")
        if not photo_file or not video_file:
            raise ValueError("Photo and video files are required")
        
        # Call API to create AR content
        # Files from form are already UploadFile objects
        result = await _create_ar_content(
            company_id=company_id,
            project_id=project_id,
            customer_name=customer_name,
            customer_phone=customer_phone if customer_phone else None,
            customer_email=customer_email if customer_email else None,
            duration_years=duration_years,
            photo_file=photo_file,
            video_file=video_file,
            db=db
        )
        
        # Redirect to AR content list after successful creation
        return RedirectResponse(url="/ar-content", status_code=303)
        
    except Exception as e:
        logger.error("ar_content_create_error", error=str(e), exc_info=True)
        # Return to form with error
        try:
            from app.api.routes.companies import list_companies
            from app.api.routes.projects import list_projects
            
            companies_result = await list_companies(
                page=1,
                page_size=100,
                search=None,
                status=None,
                db=db,
                current_user=current_user
            )
            companies = [dict(item) for item in companies_result.items]
            
            from sqlalchemy import select
            from app.models.project import Project
            from app.models.company import Company
            
            query = select(Project).join(Company)
            result = await db.execute(query)
            all_projects = result.scalars().all()
            
            projects = []
            for project in all_projects:
                projects.append({
                    "id": str(project.id),
                    "name": project.name,
                    "status": project.status,
                    "company_id": project.company_id,
                })
        except Exception:
            companies = []
            projects = []
        
        context = {
            "request": request,
            "companies": companies,
            "projects": projects,
            "companies_js": companies,
            "projects_js": projects,
            "current_user": current_user,
            "error": f"Failed to create AR content: {str(e)}"
        }
        return templates.TemplateResponse("ar-content/form.html", context)


@router.post("/ar-content/{ar_content_id}", response_class=HTMLResponse)
async def ar_content_update_post(
    ar_content_id: str,
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db)
):
    """Handle AR content update form submission."""
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        return RedirectResponse(url="/admin/login", status_code=303)
    
    try:
        # Get AR content to find company_id and project_id
        ar_content = await get_ar_content_by_id(int(ar_content_id), db)
        if not ar_content:
            return RedirectResponse(url="/ar-content", status_code=303)
        
        # Get form data
        form_data = await request.form()
        customer_name = form_data.get("customer_name", "").strip()
        customer_phone = form_data.get("customer_phone", "").strip()
        customer_email = form_data.get("customer_email", "").strip()
        duration_years = int(form_data.get("duration_years", 1))
        
        # Validation
        if not customer_name:
            raise ValueError("Customer name is required")
        if duration_years not in [1, 3, 5]:
            raise ValueError("Duration must be 1, 3, or 5 years")
        
        # Call API to update AR content
        # Convert ar_content to dict if it's a Pydantic model
        if hasattr(ar_content, 'company_id'):
            company_id = ar_content.company_id
            project_id = ar_content.project_id
        elif isinstance(ar_content, dict):
            company_id = ar_content.get('company_id')
            project_id = ar_content.get('project_id')
        else:
            # Get from database
            ar_content_db = await db.get(ARContent, int(ar_content_id))
            if not ar_content_db:
                raise ValueError("AR content not found")
            company_id = ar_content_db.company_id
            project_id = ar_content_db.project_id
        
        update_data = ARContentUpdate(
            customer_name=customer_name,
            customer_phone=customer_phone if customer_phone else None,
            customer_email=customer_email if customer_email else None,
            duration_years=duration_years
        )
        
        await update_ar_content(
            company_id=company_id,
            project_id=project_id,
            content_id=int(ar_content_id),
            update_data=update_data,
            db=db
        )
        
        # Redirect to AR content detail after successful update
        return RedirectResponse(url=f"/ar-content/{ar_content_id}", status_code=303)
        
    except Exception as e:
        logger.error("ar_content_update_error", ar_content_id=ar_content_id, error=str(e), exc_info=True)
        # Redirect back to edit form
        return RedirectResponse(url=f"/ar-content/{ar_content_id}/edit?error={str(e)}", status_code=303)


@router.get("/view/{unique_id}", response_class=HTMLResponse)
async def ar_content_viewer(
    unique_id: str,
    db: AsyncSession = Depends(get_html_db)
):
    """Public AR viewer page."""
    from app.api.routes.ar_content import get_ar_viewer
    return await get_ar_viewer(unique_id, db)
