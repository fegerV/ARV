from contextlib import asynccontextmanager
from datetime import datetime
import os
import sys
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Summary
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import init_db, seed_defaults
from app.api.routes.auth import get_current_active_user


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
    allow_origin_regex=r'https?://(localhost|127\.0\.0\.1)(:\d+)?',
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
os.makedirs("static", exist_ok=True)
app.mount("/storage", StaticFiles(directory=settings.MEDIA_ROOT), name="storage")
app.mount("/static", StaticFiles(directory="static"), name="static")


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
                "message": "Internal server error",
                "timestamp": datetime.utcnow().isoformat(),
            }
        },
    )


# Include API routers
from app.api.routes import auth, companies, projects, ar_content, storage, analytics, notifications

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(companies.router, prefix="/api/companies", tags=["Companies"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(ar_content.router, prefix="/api/ar-content", tags=["AR Content"])
app.include_router(storage.router, prefix="/api/storage", tags=["Storage"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])

# Health check endpoint
@app.get("/api/health/status")
async def health_check():
    """Health check endpoint."""
    logger = structlog.get_logger()
    
    # Check database connection
    from app.core.database import engine
    from sqlalchemy import text
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    # System metrics
    import psutil
    system_metrics = {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("/").percent if os.name != "nt" else psutil.disk_usage("C:").percent,
    }
    
    overall_status = "healthy" if db_status == "healthy" else "unhealthy"
    
    logger.info(
        "health_check",
        database=db_status,
        system=system_metrics,
        overall=overall_status,
    )
    
    return {
        "status": overall_status,
        "database": db_status,
        "system": system_metrics,
        "timestamp": datetime.utcnow().isoformat(),
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Vertex AR B2B Platform API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/health/status"
    }


# AR Viewer endpoint
@app.get("/ar/{unique_id}")
async def ar_viewer(unique_id: str):
    """Public AR viewer endpoint."""
    return templates.TemplateResponse("ar_viewer.html", {"request": {}, "unique_id": unique_id})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )