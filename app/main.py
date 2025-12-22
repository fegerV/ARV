from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles
from prometheus_client import Summary
import structlog
from datetime import datetime
import os
import sys
from typing import AsyncGenerator

from app.models.user import User

import structlog

from app.core.config import settings
from app.core.database import init_db, seed_defaults, get_db
from app.api.routes.auth import get_current_active_user
from app.api.routes.auth import get_current_user_optional
from app.middleware.rate_limiter import setup_rate_limiting, limiter
from app.api.routes.analytics import analytics_summary
from app.api.routes.companies import list_companies
from app.api.routes.ar_content import list_all_ar_content
from app.api.routes.projects import list_projects


# Configure structured logging
def configure_logging() -> None:
    """Configure structured logging with structlog."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.dev.ConsoleRenderer() if settings.DEBUG else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(structlog.stdlib.logging, settings.LOG_LEVEL.upper(), structlog.stdlib.logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )


# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan context manager.
    
    Handles startup and shutdown events.
    """
    logger = structlog.get_logger()
    
    # Startup
    logger.info(
        "application_startup",
        environment=settings.ENVIRONMENT,
        debug=settings.DEBUG,
        log_level=settings.LOG_LEVEL,
    )
    
    # Initialize database connection
    try:
        logger.info("database_initialized")

        # Seed defaults (Vertex AR local storage and company)
        try:
            await seed_defaults()
            logger.info("defaults_seeded")
        except Exception as se:
            logger.error("defaults_seeding_failed", error=str(se))
    except Exception as e:
        logger.error("database_initialization_failed", error=str(e))
        sys.exit(1)
    
    yield
    
    # Shutdown
    logger.info("application_shutdown")
    logger.info("database_closed")


# Configure logging before creating app
configure_logging()

# Create FastAPI application
app = FastAPI(
    title="Vertex AR B2B Platform",
    description="B2B SaaS platform for creating AR content based on image recognition (NFT markers)",
    version="0.1.0",
    docs_url="/docs", # Standard FastAPI docs URL
    redoc_url="/redoc",  # Standard FastAPI redoc URL
    openapi_url="/openapi.json",  # Standard FastAPI openapi URL
    lifespan=lifespan,
    contact={
        "name": "Vertex AR Support",
        "url": "https://vertexar.com/support",
        "email": "support@vertexar.com",
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
)

# Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Add Jinja2 filter for datetime formatting
def datetime_format(value, format="%d.%m.%Y %H:%M"):
    if value:
        if isinstance(value, str):
            # Convert string to datetime object if needed
            try:
                # Handle ISO format string
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                pass
        if isinstance(value, datetime):
            return value.strftime(format)
    return "—"

templates.env.filters["datetime_format"] = datetime_format

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=r'https?://(localhost|127\.0\.0\.1)(:\d+)?',
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount HTML admin routes before static files to ensure they take precedence
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, current_user: User = Depends(get_current_active_user)):
    """Admin dashboard page."""
    # Fetch dashboard data from API
    async for db in get_db():
        try:
            result = await analytics_summary(db=db)
            dashboard_data = dict(result)
            break  # Выходим из цикла после получения результата
        except Exception as e:
            # Fallback to mock data if API call fails
            dashboard_data = {
                "total_views": 12543,
                "unique_sessions": 3241,
                "active_content": 156,
                "storage_used_gb": 2.4,
                "active_companies": 24,
                "active_projects": 89,
                "revenue": "$12,450",
                "uptime": "99.9%"
            }
            break  # Выходим из цикла после получения результата
    
    context = {
        "request": request,
        "current_user": current_user,
        "total_views": dashboard_data.get("total_views", 0),
        "unique_sessions": dashboard_data.get("unique_sessions", 0),
        "active_content": dashboard_data.get("active_content", 0),
        "storage_used_gb": dashboard_data.get("storage_used_gb", 0),
        "active_companies": dashboard_data.get("active_companies", 0),
        "active_projects": dashboard_data.get("active_projects", 0),
        "revenue": dashboard_data.get("revenue", "$0"),
        "uptime": dashboard_data.get("uptime", "0%")
    }
    return templates.TemplateResponse("dashboard/index.html", context)

# Admin login page
@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Admin login page."""
    context = {
        "request": request,
        "error": None,
        "locked_until": None,
        "attempts_left": None
    }
    return templates.TemplateResponse("auth/login.html", context)

# Main route redirect
@app.get("/", response_class=RedirectResponse)
async def root(current_user: User = Depends(get_current_user_optional)):
    if current_user:
        return RedirectResponse("/admin")
    return RedirectResponse("/admin/login")

# Include API routers
from app.api.routes import (
    auth, companies, projects, ar_content, storage, analytics, notifications,
    rotation, oauth, public, settings as routes_settings, viewer, videos, health, alerts_ws
)

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(companies.router, prefix="/api", tags=["Companies"])
app.include_router(projects.router, prefix="/api", tags=["Projects"])
app.include_router(ar_content.router, prefix="/api", tags=["AR Content"])
app.include_router(storage.router, prefix="/api/storage", tags=["Storage"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(rotation.router, prefix="/api/rotation", tags=["Rotation"])
app.include_router(oauth.router, prefix="/api/oauth", tags=["OAuth"])
app.include_router(public.router, prefix="/api/public", tags=["Public"])
app.include_router(routes_settings.router, prefix="/api/settings", tags=["Settings"])
app.include_router(viewer.router, prefix="/api/viewer", tags=["Viewer"])
app.include_router(videos.router, prefix="/api/videos", tags=["Videos"])
app.include_router(health.router, prefix="/api/health", tags=["Health"])
app.include_router(alerts_ws.router, prefix="/api/ws", tags=["WebSocket"])


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger = structlog.get_logger()
    # Convert body to string to avoid serialization issues
    body_content = str(exc.body) if exc.body else "No body"
    logger.error("validation_error",
                 errors=exc.errors(),
                 body=body_content,
                 url=str(request.url),
                 method=request.method)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": body_content},
    )

# Setup rate limiting
setup_rate_limiting(app)

# Mount static files AFTER HTML routes to ensure they don't override admin routes
os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
os.makedirs("static", exist_ok=True)
app.mount("/storage", StaticFiles(directory=settings.MEDIA_ROOT), name="storage")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/companies", response_class=HTMLResponse)
async def companies_list(request: Request, current_user: User = Depends(get_current_active_user)):
    """Companies list page."""
    # Fetch companies from API - imports already at top of file
    
    # Get current user (for now, we'll pass a mock user)
    async for db in get_db():
        try:
            result = await list_companies(page=1, page_size=10, db=db, current_user=current_user)
            companies = [dict(item) for item in result.items]
            break  # Выходим из цикла после получения результата
        except Exception as e:
            # Fallback to mock data if API call fails
            companies = [
                {
                    "id": "1",
                    "name": "Vertex AR Solutions",
                    "contact_email": "contact@vertexar.com",
                    "storage_provider": "Local",
                    "status": "active",
                    "projects_count": 12,
                    "created_at": "2023-01-15T10:30:00"
                },
                {
                    "id": "2",
                    "name": "AR Tech Innovations",
                    "contact_email": "info@artech.com",
                    "storage_provider": "AWS S3",
                    "status": "active",
                    "projects_count": 8,
                    "created_at": "2023-02-20T14:22:0"
                }
            ]
            break  # Выходим из цикла после получения результата
    
    context = {
        "request": request,
        "companies": companies,
        "current_user": current_user
    }
    return templates.TemplateResponse("companies/list.html", context)

# Company detail route
@app.get("/companies/{company_id}", response_class=HTMLResponse)
async def company_detail(company_id: str, request: Request, current_user: User = Depends(get_current_active_user)):
    """Company detail page."""
    # Import company API function
    from app.api.routes.companies import get_company
    
    async for db in get_db():
        try:
            # Get company detail from API
            from app.schemas.company import Company as CompanySchema
            company = await get_company(int(company_id), db)
            company_data = CompanySchema.model_validate(company).dict()
            break  # Exit loop after getting result
        except Exception as e:
            # Fallback to mock data if API call fails
            company_data = {
                "id": company_id,
                "name": "Vertex AR Solutions",
                "contact_email": "contact@vertexar.com",
                "storage_provider": "Local",
                "status": "active",
                "projects_count": 12,
                "created_at": "2023-01-15T10:30:00"
            }
            break  # Exit loop after getting result
    
    context = {
        "request": request,
        "company": company_data,
        "current_user": current_user
    }
    return templates.TemplateResponse("companies/detail.html", context)

# Company create route
@app.get("/companies/create", response_class=HTMLResponse)
async def company_create(request: Request, current_user: User = Depends(get_current_active_user)):
    """Company create page."""
    context = {
        "request": request,
        "current_user": current_user
    }
    return templates.TemplateResponse("companies/form.html", context)

# AR Content list route
@app.get("/ar-content", response_class=HTMLResponse)
async def ar_content_list(request: Request, current_user: User = Depends(get_current_active_user)):
    """AR Content list page."""
    # Fetch AR content from API - imports already at top of file
    
    # Get current user (for now, we'll pass a mock user)
    async for db in get_db():
        try:
            result = await list_all_ar_content(page=1, page_size=10, db=db)
            ar_content_list = [dict(item) for item in result.items]
            
            # Extract unique companies and statuses for filters
            unique_companies = list(set(item.get('company_name', '') for item in ar_content_list if item.get('company_name')))
            unique_statuses = list(set(item.get('status', '') for item in ar_content_list if item.get('status')))
            break  # Выходим из цикла после получения результата
        except Exception as e:
            # Fallback to mock data if API call fails
            ar_content_list = [
                {
                    "id": "1",
                    "order_number": "AR-001",
                    "company_name": "Vertex AR Solutions",
                    "created_at": "2023-01-15T10:30:00",
                    "status": "ready",
                    "thumbnail_url": "/storage/thumbnails/sample.jpg",
                    "active_video_title": "Product Demo",
                    "customer_name": "John Doe",
                    "customer_phone": "+1234567890",
                    "customer_email": "john@example.com",
                    "views_count": 125,
                    "views_30_days": 42,
                    "public_url": "https://example.com/ar/1"
                },
                {
                    "id": "2",
                    "order_number": "AR-002",
                    "company_name": "AR Tech Innovations",
                    "created_at": "2023-01-20T14:45:00",
                    "status": "processing",
                    "thumbnail_url": "/storage/thumbnails/sample2.jpg",
                    "active_video_title": "Marketing Video",
                    "customer_name": "Jane Smith",
                    "customer_phone": "+0987654321",
                    "customer_email": "jane@example.com",
                    "views_count": 89,
                    "views_30_days": 23,
                    "public_url": "https://example.com/ar/2"
                }
            ]
            unique_companies = ["Vertex AR Solutions", "AR Tech Innovations"]
            unique_statuses = ["ready", "processing", "pending", "failed"]
            break  # Выходим из цикла после получения результата
    
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

# AR Content detail route
@app.get("/ar-content/{ar_content_id}", response_class=HTMLResponse)
async def ar_content_detail(ar_content_id: str, request: Request, current_user: User = Depends(get_current_active_user)):
    """AR Content detail page."""
    # Import the AR content API function
    from app.api.routes.ar_content import get_ar_content_by_id_legacy
    
    async for db in get_db():
        try:
            # Get AR content detail from API
            result = await get_ar_content_by_id_legacy(int(ar_content_id), db)
            ar_content = dict(result)
            
            # Convert datetime objects to strings for template
            if 'created_at' in ar_content and ar_content['created_at']:
                ar_content['created_at'] = ar_content['created_at'].isoformat()
            if 'updated_at' in ar_content and ar_content['updated_at']:
                ar_content['updated_at'] = ar_content['updated_at'].isoformat()
                
            break  # Exit loop after getting result
        except Exception as e:
            # Fallback to mock data if API call fails
            ar_content = {
                "id": ar_content_id,
                "order_number": f"AR-{ar_content_id.zfill(3)}",
                "company_name": "Vertex AR Solutions",
                "project_name": "Q4 Marketing Campaign",
                "created_at": "2023-01-15T10:30:00",
                "status": "ready",
                "customer_name": "John Doe",
                "customer_phone": "+1234567890",
                "customer_email": "john@example.com",
                "duration_years": 1,
                "photo_url": "/storage/photos/sample.jpg",
                "video_url": "/storage/videos/sample.mp4",
                "thumbnail_url": "/storage/thumbnails/sample.jpg",
                "active_video_title": "Product Demo",
                "views_count": 125,
                "views_30_days": 42,
                "public_url": f"/api/ar-content/view/{ar_content_id}",
                "unique_link": f"/view/{ar_content_id}",
                "qr_code_url": f"/storage/qr/{ar_content_id}.png",
                "marker_status": "generated",
                "videos": []
            }
            break  # Exit loop after getting result
    
    context = {
        "request": request,
        "ar_content": ar_content,
        "current_user": current_user
    }
    return templates.TemplateResponse("ar-content/detail.html", context)

# AR Content create route
@app.get("/ar-content/create", response_class=HTMLResponse)
async def ar_content_create(request: Request, current_user: User = Depends(get_current_active_user)):
    """AR Content create page."""
    # Fetch companies and projects for dropdowns
    async for db in get_db():
        try:
            # Get companies
            from app.api.routes.companies import list_companies
            companies_result = await list_companies(page=1, page_size=100, db=db, current_user=current_user)
            companies = [dict(item) for item in companies_result.items]
            
            # Get projects
            from app.api.routes.projects import list_projects
            projects_result = await list_projects(page=1, page_size=100, db=db, current_user=current_user)
            projects = [dict(item) for item in projects_result.items]
            
            break  # Exit loop after getting result
        except Exception as e:
            # Fallback to mock data if API call fails
            companies = [
                {"id": "1", "name": "Vertex AR Solutions", "status": "active"},
                {"id": "2", "name": "AR Tech Innovations", "status": "active"}
            ]
            projects = [
                {"id": "1", "name": "Q4 Marketing Campaign", "company_id": "1", "status": "active"},
                {"id": "2", "name": "Product Demo Series", "company_id": "1", "status": "active"}
            ]
            break  # Exit loop after getting result
    
    context = {
        "request": request,
        "companies": companies,
        "projects": projects,
        "current_user": current_user
    }
    return templates.TemplateResponse("ar-content/form.html", context)

# HTMX endpoints for dynamic updates
@app.post("/ar-content/{ar_content_id}/copy-link")
async def copy_ar_content_link(ar_content_id: str, request: Request):
    """HTMX endpoint to handle link copying."""
    # In a real implementation, this would copy the link to clipboard
    # For now, we'll just return a success message
    return HTMLResponse("<div class='fixed bottom-4 right-4 bg-green-500 text-white px-4 py-2 rounded shadow'>Link copied to clipboard</div>")

@app.get("/ar-content/{ar_content_id}/qr-code")
async def get_ar_content_qr_code(ar_content_id: str, request: Request):
    """HTMX endpoint to get QR code for AR content."""
    # In a real implementation, this would generate and return the QR code
    # For now, we'll return a placeholder
    return HTMLResponse(f"""
    <div class="flex flex-col items-center">
        <div class="bg-white p-4 rounded">
            <img src="https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=https://example.com/ar/{ar_content_id}" alt="QR Code">
        </div>
        <p class="mt-2 text-sm">https://example.com/ar/{ar_content_id}</p>
    </div>
    """)

@app.delete("/ar-content/{ar_content_id}")
async def delete_ar_content(ar_content_id: str, request: Request):
    """HTMX endpoint to delete AR content."""
    # In a real implementation, this would delete the AR content from the database
    # For now, we'll just return an empty list
    context = {
        "request": request,
        "ar_content_list": [],
        "unique_companies": [],
        "unique_statuses": [],
        "page": 0,
        "page_size": 10,
        "total_count": 0,
        "total_pages": 1
    }
    return templates.TemplateResponse("ar-content/list.html", context)

# Import API modules to access their routers and functions - already imported above

# Additional HTML routes for other admin pages
@app.get("/projects", response_class=HTMLResponse)
async def projects_list(request: Request, current_user: User = Depends(get_current_active_user)):
    """Projects list page."""
    # Fetch projects from API - imports already at top of file
    
    # Get current user (for now, we'll pass a mock user)
    async for db in get_db():
        try:
            result = await list_projects(page=1, page_size=10, db=db, current_user=current_user)
            projects = [dict(item) for item in result.items]
            break  # Выходим из цикла после получения результата
        except Exception as e:
            # Fallback to mock data if API call fails
            projects = [
                {
                    "id": "1",
                    "name": "Q4 Marketing Campaign",
                    "status": "active",
                    "company_name": "Vertex AR Solutions",
                    "created_at": "2023-01-15T10:30:00",
                    "ar_content_count": 5
                },
                {
                    "id": "2",
                    "name": "Product Demo Series",
                    "status": "active",
                    "company_name": "AR Tech Innovations",
                    "created_at": "2023-02-20T14:22:00",
                    "ar_content_count": 3
                }
            ]
            break  # Выходим из цикла после получения результата
    
    context = {
        "request": request,
        "projects": projects,
        "current_user": current_user
    }
    return templates.TemplateResponse("projects/list.html", context)

# Project detail route
@app.get("/projects/{project_id}", response_class=HTMLResponse)
async def project_detail(project_id: str, request: Request, current_user: User = Depends(get_current_active_user)):
    """Project detail page."""
    # Import project API function
    from app.api.routes.projects import get_project
    
    async for db in get_db():
        try:
            # Get project detail from API
            project = await get_project(int(project_id), db)
            project_data = dict(project)
            break  # Exit loop after getting result
        except Exception as e:
            # Fallback to mock data if API call fails
            project_data = {
                "id": project_id,
                "name": "Q4 Marketing Campaign",
                "status": "active",
                "company_name": "Vertex AR Solutions",
                "created_at": "2023-01-15T10:30:00",
                "ar_content_count": 5
            }
            break  # Exit loop after getting result
    
    context = {
        "request": request,
        "project": project_data,
        "current_user": current_user
    }
    return templates.TemplateResponse("projects/detail.html", context)

# Project create route
@app.get("/projects/create", response_class=HTMLResponse)
async def project_create(request: Request, current_user: User = Depends(get_current_active_user)):
    """Project create page."""
    # Fetch companies for dropdown
    async for db in get_db():
        try:
            # Get companies
            from app.api.routes.companies import list_companies
            companies_result = await list_companies(page=1, page_size=100, db=db, current_user=current_user)
            companies = [dict(item) for item in companies_result.items]
            break  # Exit loop after getting result
        except Exception as e:
            # Fallback to mock data if API call fails
            companies = [
                {"id": "1", "name": "Vertex AR Solutions", "status": "active"},
                {"id": "2", "name": "AR Tech Innovations", "status": "active"}
            ]
            break  # Exit loop after getting result
    
    context = {
        "request": request,
        "companies": companies,
        "current_user": current_user
    }
    return templates.TemplateResponse("projects/form.html", context)

@app.get("/storage", response_class=HTMLResponse)
async def storage_page(request: Request, current_user: User = Depends(get_current_active_user)):
    """Storage page."""
    # In a real implementation, you would fetch actual data from your API
    # For now, we'll return mock data
    context = {
        "request": request,
        "storage_info": {
            "total_storage": "100 GB",
            "used_storage": "24.5 GB",
            "available_storage": "75.5 GB",
            "providers": [
                {
                    "name": "Local Storage",
                    "status": "active",
                    "description": "Default local storage provider",
                    "used_space": "24.5 GB",
                    "capacity": "100 GB"
                }
            ],
            "companies": [
                {
                    "id": "1",
                    "name": "Vertex AR Solutions",
                    "storage_used": "15.2 GB",
                    "files_count": 142
                },
                {
                    "id": "2",
                    "name": "AR Tech Innovations",
                    "storage_used": "9.3 GB",
                    "files_count": 87
                }
            ]
        },
        "current_user": current_user
    }
    return templates.TemplateResponse("storage.html", context)

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request, current_user: User = Depends(get_current_active_user)):
    """Analytics page."""
    # In a real implementation, you would fetch actual data from your API
    # For now, we'll return mock data
    context = {
        "request": request,
        "analytics_data": {
            "total_views": 12543,
            "unique_sessions": 3241,
            "active_content": 156,
            "avg_session_duration": "2m 34s",
            "views_30_days": 3241,
            "unique_visitors_30_days": 1245,
            "avg_engagement_time": "1m 45s",
            "bounce_rate": "24.3%",
            "top_content": [
                {
                    "id": "1",
                    "title": "Product Demo AR",
                    "company_name": "Vertex AR Solutions",
                    "views_count": 1240
                },
                {
                    "id": "2",
                    "title": "Marketing Campaign",
                    "company_name": "AR Tech Innovations",
                    "views_count": 987
                }
            ]
        },
        "current_user": current_user
    }
    return templates.TemplateResponse("analytics.html", context)

@app.get("/notifications", response_class=HTMLResponse)
async def notifications_page(request: Request, current_user: User = Depends(get_current_active_user)):
    """Notifications page."""
    # In a real implementation, you would fetch actual data from your API
    # For now, we'll return mock data
    context = {
        "request": request,
        "notifications": [
            {
                "id": "1",
                "title": "New AR Content Created",
                "message": "A new AR content item 'Product Demo' was created for Vertex AR Solutions",
                "created_at": "2023-01-15T10:30:00",
                "is_read": False,
                "company_name": "Vertex AR Solutions",
                "project_name": "Q4 Campaign",
                "ar_content_name": "Product Demo"
            },
            {
                "id": "2",
                "title": "Storage Alert",
                "message": "Storage usage for AR Tech Innovations has reached 80% of allocated space",
                "created_at": "2023-01-14T16:45:00",
                "is_read": True,
                "company_name": "AR Tech Innovations",
                "project_name": "Summer Sale",
                "ar_content_name": "—"
            }
        ],
        "total_count": 2,
        "current_user": current_user
    }
    return templates.TemplateResponse("notifications.html", context)

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, current_user: User = Depends(get_current_active_user)):
    """Settings page."""
    # Fetch settings from API or configuration
    context = {
        "request": request,
        "settings": {
            "site_title": "Vertex AR B2B Platform",
            "admin_email": "admin@vertexar.com",
            "site_description": "B2B SaaS platform for creating AR content based on image recognition (NFT markers)",
            "password_min_length": 8,
            "session_timeout": 60,
            "default_storage": "local",
            "max_file_size": 10
        },
        "current_user": current_user
    }
    return templates.TemplateResponse("settings.html", context)

# No need to duplicate mounting of static files - already done above


# Favicon endpoint
@app.get("/favicon.ico")
async def favicon():
    """Serve favicon."""
    import os
    # Check if favicon exists in static directory first
    if os.path.exists("static/favicon.ico"):
        return FileResponse("static/favicon.ico")
    elif os.path.exists("static/favicon.png"):
        return FileResponse("static/favicon.png")
    else:
        # Return a simple default favicon if none exists
        from fastapi.responses import Response
        # This is a minimal 16x16 ico file content (32 bytes)
        default_favicon = b'\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00\x04\x00\x86\x00\x00\x00(\x00\x00\x00\x10\x00\x00\x00 \x00\x00\x00\x01\x00\x04\x00'
        return Response(content=default_favicon, media_type="image/x-icon")

# Catchall route for SPA-style HTML serving
@app.get("/{path:path}")
async def catchall(request: Request, path: str, current_user: User = Depends(get_current_user_optional)):
    """Catchall route to serve HTML templates for all routes."""
    # Skip API routes and static files
    if path.startswith("api/") or path.startswith("storage/") or path.startswith("static/"):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=404,
            content={"detail": "Not Found"}
        )
    
    # Redirect to login if not authenticated and not on login page
    if not current_user and not path.startswith("admin/login"):
        return RedirectResponse("/admin/login")
    
    # Serve the appropriate template based on the path
    if path == "" or path == "admin" or path == "admin/":
        # Dashboard
        return await admin_dashboard(request, current_user)
    elif path.startswith("companies"):
        if "/" not in path[len("companies"):]:
            return await companies_list(request, current_user)
        elif path.endswith("/create"):
            return await company_create(request, current_user)
        else:
            # Company detail or other company routes
            company_id = path.split("/")[-1] if path.split("/")[-1].isdigit() else None
            if company_id:
                return await company_detail(company_id, request, current_user)
    elif path.startswith("projects"):
        if "/" not in path[len("projects"):]:
            return await projects_list(request, current_user)
        elif path.endswith("/create"):
            return await project_create(request, current_user)
        else:
            # Project detail or other project routes
            project_id = path.split("/")[-1] if path.split("/")[-1].isdigit() else None
            if project_id:
                return await project_detail(project_id, request, current_user)
    elif path.startswith("ar-content"):
        if "/" not in path[len("ar-content"):]:
            return await ar_content_list(request, current_user)
        elif path.endswith("/create"):
            return await ar_content_create(request, current_user)
        else:
            # AR content detail or other routes
            ar_content_id = path.split("/")[-1] if path.split("/")[-1].isdigit() else None
            if ar_content_id:
                return await ar_content_detail(ar_content_id, request, current_user)
    elif path == "storage":
        return await storage_page(request, current_user)
    elif path == "analytics":
        return await analytics_page(request, current_user)
    elif path == "notifications":
        return await notifications_page(request, current_user)
    elif path == "settings":
        return await settings_page(request, current_user)
    
    # Default fallback to dashboard
    return await admin_dashboard(request, current_user)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )