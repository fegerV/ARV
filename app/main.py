from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
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

import structlog

from app.core.config import settings
from app.core.database import init_db, seed_defaults
from app.api.routes.auth import get_current_active_user
from app.middleware.rate_limiter import setup_rate_limiting, limiter


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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=r'https?://(localhost|127\.0\.0\.1)(:\d+)?',
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom static files handler to support React Router client-side routing with no cache
class NoCacheStaticFiles(StaticFiles):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def get_response(self, path: str, scope):
        # Add logging to debug the path
        logger = structlog.get_logger()
        logger.info("NoCacheStaticFiles.get_response", path=path, scope_path=scope.get("path"))
        
        try:
            response = await super().get_response(path, scope)
            # Only return index.html for 404s that are not API routes or special paths
            if response.status_code == 404 and not path.startswith("api/") and not path.startswith("/api/"):
                # Check if this looks like a client-side route (no file extension, or specific frontend routes)
                if '.' not in path or path.startswith('ar-content') or path.startswith('view') or path.startswith('companies') or path.startswith('projects'):
                    logger.info("Returning index.html for client-side route", path=path)
                    # Return index.html for client-side routing
                    response = await super().get_response("index.html", scope)
            # Add no-cache headers
            if response.status_code == 200:
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
            return response
        except Exception as e:
            logger.error("NoCacheStaticFiles exception", error=str(e), path=path)
            # Check if this looks like a client-side route before returning index.html
            if '.' not in path or path.startswith('ar-content') or path.startswith('view') or path.startswith('companies') or path.startswith('projects'):
                # Return index.html for any error on client-side routes - this enables client-side routing
                return await super().get_response("index.html", scope)
            else:
                # Re-raise the exception for actual static file errors
                raise

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

# Serve static files
os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
os.makedirs("static", exist_ok=True)
app.mount("/storage", StaticFiles(directory=settings.MEDIA_ROOT), name="storage")
app.mount("/", NoCacheStaticFiles(directory="static", html=True), name="static")

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




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )