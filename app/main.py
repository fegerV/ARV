import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, ORJSONResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import logging
import structlog
import os
from typing import AsyncGenerator
from uuid import UUID

# Подстроки путей типичных сканеров/эксплойтов — не логируем 404/405 по ним (не засоряем журнал)
_ACCESS_LOG_PROBE_PATTERNS = (
    "phpunit",
    "eval-stdin.php",
    "think/app",
    "invokefunction",
    "pearcmd",
    "config-create",
    "/containers/json",
    ".php",
    "wp-",
    "wp_content",
    "xmlrpc",
    ".env",
    "phpinfo",
    "shell.",
    "cmd.",
    "PROPFIND",  # WebDAV-пробы, часто 405
    "allow_url_include",
    "auto_prepend_file",
    "php://input",
)

from app.core.config import settings  # noqa: E402
from app.core.database import seed_defaults  # noqa: E402
from app.middleware.maintenance import MaintenanceModeMiddleware  # noqa: E402
from app.middleware.rate_limiter import setup_rate_limiting  # noqa: E402
from app.middleware.site_context import SiteContextMiddleware  # noqa: E402


class _AccessLogProbeFilter(logging.Filter):
    """Не пропускать в access-лог запросы 404/405 по известным путям сканеров (PHP, Docker и т.д.)."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        if " 404 " not in msg and " 405 " not in msg:
            return True
        msg_lower = msg.lower()
        if any(p.lower() in msg_lower for p in _ACCESS_LOG_PROBE_PATTERNS):
            return False
        return True


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
    # Уменьшаем шум от сканеров в access-логе uvicorn (404/405 по путям PHP/Docker и т.д.)
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.addFilter(_AccessLogProbeFilter())


# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan context manager.

    Handles startup and shutdown events.
    """

    # Startup
    # Suppress ConnectionResetError (WinError 10054) in asyncio callbacks when client closes connection
    def _asyncio_exception_handler(loop: asyncio.AbstractEventLoop, context: dict) -> None:
        exc = context.get("exception")
        if exc is not None:
            if isinstance(exc, ConnectionResetError):
                if getattr(exc, "winerror", None) == 10054:
                    return  # suppress log
            if isinstance(exc, OSError) and getattr(exc, "winerror", None) == 10054:
                return
        loop.default_exception_handler(context)

    try:
        asyncio.get_running_loop().set_exception_handler(_asyncio_exception_handler)
    except RuntimeError:
        pass

    # ── Sentry (error tracking) ─────────────────────────────────────
    if settings.SENTRY_DSN:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                environment=settings.ENVIRONMENT,
                traces_sample_rate=0.1 if settings.is_production else 1.0,
                integrations=[FastApiIntegration(), SqlalchemyIntegration()],
                send_default_pii=False,
            )
            logger.info("sentry_initialised", environment=settings.ENVIRONMENT)
        except ImportError:
            logger.warning("sentry_sdk_not_installed")
        except Exception as exc:
            logger.error("sentry_init_failed", error=str(exc))

    logger.info(
        "application_startup",
        environment=settings.ENVIRONMENT,
        debug=settings.DEBUG,
        log_level=settings.LOG_LEVEL,
    )

    # Log storage configuration
    logger.info(
        "storage_config",
        storage_base_path=str(Path(settings.STORAGE_BASE_PATH).resolve()),
        local_storage_path=str(Path(settings.LOCAL_STORAGE_PATH).resolve()),
    )
    db_kind = "sqlite" if "sqlite" in settings.DATABASE_URL else "postgres"
    logger.info("database_config", database=db_kind)

    try:
        settings.validate_sensitive_defaults()
    except ValueError as exc:
        logger.error("insecure_defaults_detected", error=str(exc))
        raise

    # Seed defaults (Vertex AR local storage and company)
    try:
        await seed_defaults()
        logger.info("defaults_seeded")
    except Exception as se:
        logger.error("defaults_seeding_failed", error=str(se))

    # Start backup scheduler
    try:
        from app.core.scheduler import init_scheduler

        await init_scheduler()
    except Exception as exc:
        logger.error("scheduler_startup_failed", error=str(exc))

    yield

    # Shutdown
    try:
        from app.core.scheduler import scheduler as _sched

        if _sched.running:
            _sched.shutdown(wait=False)
            logger.info("scheduler_stopped")
    except Exception:
        pass
    logger.info("application_shutdown")
    logger.info("database_closed")


# Configure logging before creating app
configure_logging()

# Initialize logger after logging is configured
logger = structlog.get_logger()

# Disable OpenAPI docs in production (security best-practice)
_docs_url = None if settings.is_production else "/docs"
_redoc_url = None if settings.is_production else "/redoc"
_openapi_url = None if settings.is_production else "/openapi.json"

# Create FastAPI application
app = FastAPI(
    title="Vertex AR B2B Platform",
    description="B2B SaaS platform for creating AR content based on image recognition (NFT markers)",
    version="0.1.0",
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    openapi_url=_openapi_url,
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
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


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# GZip middleware for compressing responses
app.add_middleware(
    GZipMiddleware,
    minimum_size=500,
)

# Maintenance mode — returns 503 for public routes when enabled in settings
app.add_middleware(MaintenanceModeMiddleware)

# Inject site_title from DB settings into request.state for templates
app.add_middleware(SiteContextMiddleware)


# ── X-Request-ID middleware (request tracing) ────────────────────────
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Attach a unique request ID to every request for log correlation."""
    from uuid import uuid4

    request_id = request.headers.get("x-request-id") or str(uuid4())
    # Bind to structlog context so every log line includes request_id
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Include HTML routes
from app.html import html_router  # noqa: E402

app.include_router(html_router)

# Include API routers
from app.api.routes import (  # noqa: E402
    auth,
    companies,
    projects,
    ar_content,
    storage,
    analytics,
    notifications,
    rotation,
    oauth,
    public,
    settings as routes_settings,
    viewer,
    videos,
    health,
    alerts_ws,
    backups,
)

# Health must be registered before ar_content (which has greedy /{content_id} under /api)
app.include_router(health.router, prefix="/api/health", tags=["Health"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(storage.router, prefix="/api/storage", tags=["Storage"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(rotation.router, prefix="/api/rotation", tags=["Rotation"])
app.include_router(oauth.router, prefix="/api/oauth", tags=["OAuth"])
app.include_router(public.router, prefix="/api/public", tags=["Public"])
app.include_router(routes_settings.router, prefix="/api/settings", tags=["Settings"])
app.include_router(viewer.router, prefix="/api/viewer", tags=["Viewer"])
app.include_router(videos.router, prefix="/api/videos", tags=["Videos"])
app.include_router(alerts_ws.router, prefix="/api/ws", tags=["WebSocket"])
app.include_router(backups.router, prefix="/api/backups", tags=["Backups"])
app.include_router(companies.router, prefix="/api", tags=["Companies"])
app.include_router(projects.router, prefix="/api", tags=["Projects"])
# ar_content last: has greedy GET /{content_id} that matches any /api/... path
app.include_router(ar_content.router, prefix="/api", tags=["AR Content"])


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger = structlog.get_logger()
    # Convert body to string to avoid serialization issues
    body_content = str(exc.body) if exc.body else "No body"
    logger.error(
        "validation_error", errors=exc.errors(), body=body_content, url=str(request.url), method=request.method
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": body_content},
    )


# Setup rate limiting
setup_rate_limiting(app)


# Add specific route handlers for protected API paths BEFORE mounting static files
# This ensures that API routes return proper 404 JSON responses instead of serving static files
@app.get("/api/{path:path}")
async def api_protected_route(request: Request, path: str):
    """Protected API route that returns 404 JSON for any unmatched API paths."""
    return JSONResponse(status_code=404, content={"detail": "Not Found"})


# AR viewer landing page: /view/{unique_id} — Level 3 fallback (photo + video overlay) + app buttons
_viewer_templates = Jinja2Templates(directory="templates")


@app.get("/view/{unique_id}", response_class=HTMLResponse)
async def ar_viewer_landing(request: Request, unique_id: str):
    """Landing page: photo + video overlay (100% fallback), buttons to open AR app or download."""
    from app.api.routes.viewer import _parse_demo_index

    # Allow demo_1..demo_5 in addition to UUID
    if _parse_demo_index(unique_id) is None:
        try:
            UUID(unique_id)
        except (ValueError, TypeError):
            return JSONResponse(status_code=400, content={"detail": "Invalid unique_id format"})

    try:
        from app.core.database import AsyncSessionLocal
        from app.api.routes.viewer import get_viewer_landing_data

        async with AsyncSessionLocal() as db:
            data = await get_viewer_landing_data(unique_id, db)

        if not data:
            return JSONResponse(status_code=404, content={"detail": "AR content not found or unavailable"})

        deep_link = f"arv://view/{unique_id}"
        play_store_url = "https://play.google.com/store/apps/details?id=ru.neuroimagen.arviewer"
        app_store_url = (settings.APP_STORE_URL or "").strip()

        return _viewer_templates.TemplateResponse(
            "viewer.html",
            {
                "request": request,
                "unique_id": unique_id,
                "photo_url": data["photo_url"],
                "video_url": data.get("video_url"),
                "order_number": data.get("order_number", "AR"),
                "app_url": deep_link,
                "play_url": play_store_url,
                "appstore_url": app_store_url or "",
            },
        )
    except Exception as exc:
        logger.error("ar_viewer_landing_error", unique_id=unique_id, error=str(exc))
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Legacy QR / links: old path /ar/{unique_id} → /view/{unique_id}
@app.get("/ar/{unique_id}")
async def legacy_ar_viewer_redirect(unique_id: str):
    """Redirect legacy /ar/{unique_id} (old QR codes) to current /view/{unique_id}."""
    from app.api.routes.viewer import _parse_demo_index

    if _parse_demo_index(unique_id) is None:
        try:
            UUID(unique_id)
        except (ValueError, TypeError):
            return JSONResponse(status_code=400, content={"detail": "Invalid unique_id format"})
    return RedirectResponse(url=f"/view/{unique_id}", status_code=302)


# Android App Links: Digital Asset Links for https://your-domain.com/view/{unique_id}
@app.get("/.well-known/assetlinks.json")
async def well_known_assetlinks():
    """
    Serve assetlinks.json for Android App Links verification.
    Set ANDROID_APP_SHA256_FINGERPRINTS (comma-separated) in env to enable.
    """
    fingerprints = [s.strip() for s in settings.ANDROID_APP_SHA256_FINGERPRINTS.split(",") if s.strip()]
    statements = []
    if fingerprints and settings.ANDROID_APP_PACKAGE:
        statements = [
            {
                "relation": ["delegate_permission/common.handle_all_urls"],
                "target": {
                    "namespace": "android_app",
                    "package_name": settings.ANDROID_APP_PACKAGE,
                    "sha256_cert_fingerprints": fingerprints,
                },
            }
        ]
    return JSONResponse(
        content=statements,
        media_type="application/json",
    )


# Mount static files - StaticFiles will handle 404s automatically
# NOTE: For production, consider serving static files through Nginx instead of Uvicorn
# to avoid blocking I/O operations in a single worker environment
os.makedirs(settings.STORAGE_BASE_PATH, exist_ok=True)
os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
os.makedirs("static", exist_ok=True)
# Mount storage using STORAGE_BASE_PATH (where AR content files are actually stored)
storage_base = Path(settings.STORAGE_BASE_PATH).resolve()
storage_dir = str(storage_base.resolve())

# Mount StaticFiles for storage
app.mount("/storage", StaticFiles(directory=storage_dir), name="storage")
app.mount("/static", StaticFiles(directory="static"), name="static")

logger.info("storage_mounted", storage_dir=storage_dir)


# Favicon: один ответ для /favicon.ico и /admin/favicon.ico (браузер запрашивает по пути страницы)
def _favicon_response() -> FileResponse | Response:
    """Возвращает favicon из static/templates или дефолтную иконку."""
    for path in ("static/favicon.ico", "static/favicon.png", "templates/favicon.png"):
        if os.path.exists(path):
            return FileResponse(path, media_type="image/png" if path.endswith(".png") else "image/x-icon")
    default_favicon = (
        b"\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00\x04\x00\x86\x00\x00\x00"
        b"(\x00\x00\x00\x10\x00\x00\x00 \x00\x00\x00\x01\x00\x04\x00"
    )
    return Response(content=default_favicon, media_type="image/x-icon")


@app.get("/favicon.ico")
async def favicon():
    """Favicon для корня сайта."""
    return _favicon_response()


@app.get("/admin/favicon.ico")
async def admin_favicon():
    """Favicon для страниц /admin/* (убирает 404 в логах при открытии /admin/login)."""
    return _favicon_response()


if __name__ == "__main__":
    import uvicorn

    # 0.0.0.0 — доступ с других устройств (в т.ч. через ngrok для теста AR на телефоне)
    run_kw: dict = {
        "host": "0.0.0.0",
        "port": 8000,
        "reload": settings.DEBUG,
        "log_level": settings.LOG_LEVEL.lower(),
    }
    if settings.ssl_enabled:
        run_kw["ssl_keyfile"] = settings.SSL_KEYFILE
        run_kw["ssl_certfile"] = settings.SSL_CERTFILE
    uvicorn.run("app.main:app", **run_kw)
