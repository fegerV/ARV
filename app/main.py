import sys
import structlog
from datetime import datetime
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from prometheus_client import Summary
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.database import init_db, close_db, seed_defaults


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
        await init_db()
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
    await close_db()
    logger.info("database_closed")


# Configure logging before creating app
configure_logging()

# Create FastAPI application
app = FastAPI(
    title="Vertex AR B2B Platform",
    description="B2B SaaS platform for creating AR content based on image recognition (NFT markers)",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Jinja2 templates
templates = Jinja2Templates(directory="templates")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
REQUEST_DURATION = Summary('api_request_duration_seconds', 'API request duration seconds', ['method','path'])
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log all HTTP requests with structured logging."""
    logger = structlog.get_logger()
    
    start_time = datetime.utcnow()
    
    # Log request
    logger.info(
        "http_request_started",
        method=request.method,
        path=request.url.path,
        client_host=request.client.host if request.client else None,
    )
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = (datetime.utcnow() - start_time).total_seconds()
    REQUEST_DURATION.labels(request.method, request.url.path).observe(duration)
    
    # Log response
    logger.info(
        "http_request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_seconds=duration,
    )
    
    return response


# Exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions."""
    logger = structlog.get_logger()
    logger.warning(
        "http_exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "timestamp": datetime.utcnow().isoformat(),
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    logger = structlog.get_logger()
    logger.warning(
        "validation_error",
        errors=exc.errors(),
        path=request.url.path,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": 422,
                "message": "Validation error",
                "details": exc.errors(),
                "timestamp": datetime.utcnow().isoformat(),
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions."""
    logger = structlog.get_logger()
    logger.error(
        "unhandled_exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error" if not settings.DEBUG else str(exc),
                "timestamp": datetime.utcnow().isoformat(),
            }
        },
    )


# Health check endpoints
# Health endpoints moved to app.api.routes.health


# Readiness endpoint removed; use /api/health/status for checks


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "message": "Vertex AR B2B Platform API",
        "version": app.version,
        "docs": "/docs",
        "health": "/api/health/status",
    }


# Include API routers (will be added in next phases)
from app.api.routes import companies as companies_router
from app.api.routes import projects as projects_router
from app.api.routes import ar_content as ar_content_router
from app.api.routes import storage as storage_router
from app.api.routes import videos as videos_router
from app.api.routes import rotation as rotation_router
from app.api.routes import analytics as analytics_router
from app.api.routes import notifications as notifications_router
from app.api.routes import oauth as oauth_router
from app.api.routes import public as public_router
from app.api.routes import health as health_router
from app.api.routes import alerts_ws as alerts_ws_router
from app.api.routes import auth as auth_router
from app.api.routes import viewer as viewer_router

# Include routers with appropriate prefixes
app.include_router(companies_router.router, prefix="/api/companies", tags=["Companies"])
# app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
# app.include_router(ar_content.router, prefix="/api/ar-content", tags=["AR Content"])
# app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"]) 
app.include_router(storage_router.router, prefix="/api", tags=["Storage"]) 
app.include_router(projects_router.router, prefix="/api", tags=["Projects"]) 
app.include_router(ar_content_router.router, prefix="/api", tags=["AR Content"]) 
# Removed duplicate companies router inclusion
app.include_router(videos_router.router, prefix="/api", tags=["Videos"]) 
app.include_router(rotation_router.router, prefix="/api", tags=["Rotation"]) 
app.include_router(analytics_router.router, prefix="/api", tags=["Analytics"]) 
app.include_router(notifications_router.router, prefix="/api", tags=["Notifications"]) 
app.include_router(oauth_router.router)
app.include_router(public_router.router, prefix="/api", tags=["Public"])
app.include_router(health_router.router)
app.include_router(alerts_ws_router.router)
app.include_router(auth_router.router, prefix="/api", tags=["Authentication"])
app.include_router(viewer_router.router, prefix="/api", tags=["Viewer"])


# Public AR Viewer endpoints
@app.get("/ar/{unique_id}", tags=["AR"])
async def ar_viewer(unique_id: str, request: Request):
    """AR viewer template endpoint (legacy path)."""
    return templates.TemplateResponse("ar_viewer.html", {"request": request, "unique_id": unique_id})


@app.get("/ar-content/{unique_id}", tags=["AR"])
async def ar_viewer_new(unique_id: str, request: Request):
    """AR viewer template endpoint (new clean path)."""
    return templates.TemplateResponse("ar_viewer.html", {"request": request, "unique_id": unique_id})
