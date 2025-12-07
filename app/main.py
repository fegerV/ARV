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
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

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

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI application
app = FastAPI(
    title="Vertex AR B2B Platform",
    description="B2B SaaS platform for creating AR content based on image recognition (NFT markers)",
    version="2.0.0",  # Синхронизировано с core.config.VERSION
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Add rate limiter middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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


# Enhanced logging middleware with request ID, user ID, and company ID
from app.core.logging_middleware import logging_middleware as enhanced_logging_middleware

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Enhanced logging middleware with structured logging and request tracking."""
    return await enhanced_logging_middleware(request, call_next)


# Exception handlers
from app.core.errors import setup_exception_handlers

# Setup exception handlers
setup_exception_handlers(app)


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
from app.api.routes import portraits as portraits_router
from app.api.routes import storage as storage_router
from app.api.routes import projects as projects_router
from app.api.routes import ar_content as ar_content_router
from app.api.routes import companies as companies_router
from app.api.routes import videos as videos_router
from app.api.routes import rotation as rotation_router
from app.api.routes import analytics as analytics_router
from app.api.routes import notifications as notifications_router
from app.api.routes import oauth as oauth_router
from app.api.routes import public as public_router
from app.api.routes import health as health_router
from app.api.routes import alerts_ws as alerts_ws_router
from app.api.routes import auth as auth_router
# app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
# app.include_router(companies.router, prefix="/api/companies", tags=["Companies"])
# app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
# app.include_router(ar_content.router, prefix="/api/ar-content", tags=["AR Content"])
# app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"]) 
app.include_router(auth_router.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(portraits_router.router, prefix="/api", tags=["Portraits"])
app.include_router(storage_router.router, prefix="/api", tags=["Storage"]) 
app.include_router(projects_router.router, prefix="/api", tags=["Projects"]) 
app.include_router(ar_content_router.router, prefix="/api", tags=["AR Content"]) 
app.include_router(companies_router.router) 
app.include_router(videos_router.router, prefix="/api", tags=["Videos"]) 
app.include_router(rotation_router.router, prefix="/api", tags=["Rotation"]) 
app.include_router(analytics_router.router, prefix="/api", tags=["Analytics"]) 
app.include_router(notifications_router.router, prefix="/api", tags=["Notifications"]) 
app.include_router(oauth_router.router)
app.include_router(public_router.router, prefix="/api", tags=["Public"])
app.include_router(health_router.router)
app.include_router(alerts_ws_router.router)


# Public AR Viewer endpoint
@app.get("/ar/{unique_id}", tags=["AR"])
async def ar_viewer(unique_id: str, request: Request):
    return templates.TemplateResponse("ar_viewer.html", {"request": request, "portrait_id": unique_id})
