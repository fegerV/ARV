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
    docs_url="/docs",  # Standard FastAPI docs URL
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

# Custom static files handler to support React Router client-side routing
class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        # Add logging to debug the path
        logger = structlog.get_logger()
        logger.info("SPAStaticFiles.get_response", path=path, scope_path=scope.get("path"))
        
        try:
            response = await super().get_response(path, scope)
            # Only return index.html for 404s that are not API routes
            if response.status_code == 404 and not path.startswith("api/") and not path.startswith("/api/"):
                logger.info("Returning index.html for 404", path=path)
                # Return index.html for any 404 - this enables client-side routing
                response = await super().get_response("index.html", scope)
            return response
        except Exception as e:
            logger.error("SPAStaticFiles exception", error=str(e), path=path)
            # Return index.html for any error - this enables client-side routing
            return await super().get_response("index.html", scope)

# Include API routers
from app.api.routes import (
    auth, companies, projects, ar_content, storage, analytics, notifications,
    rotation, oauth, public, settings as routes_settings, viewer, videos, health, alerts_ws
)

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(companies.router, prefix="/api", tags=["Companies"])
app.include_router(projects.router, prefix="/api", tags=["Projects"])
app.include_router(ar_content.router, prefix="/api/ar-content", tags=["AR Content"])
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

# Setup rate limiting
setup_rate_limiting(app)

# Serve static files
os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
os.makedirs("static", exist_ok=True)
app.mount("/storage", StaticFiles(directory=settings.MEDIA_ROOT), name="storage")
app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")

# Favicon endpoint
@app.get("/favicon.ico")
async def favicon():
    """Serve favicon."""
    return FileResponse("templates/favicon.png")


# Catch-all route for React Router client-side routing
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serve the frontend application for any unmatched routes (enables client-side routing)."""
    # Don't serve frontend for API routes
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )