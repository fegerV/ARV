from fastapi import APIRouter
from .routes import (
    auth, dashboard, companies, projects, ar_content,
    storage, analytics, notifications, settings, htmx
)

html_router = APIRouter(prefix="", tags=["HTML"])

# регистрируем все под-роутеры
html_router.include_router(auth.router)
html_router.include_router(dashboard.router)
html_router.include_router(companies.router)
html_router.include_router(projects.router)
html_router.include_router(ar_content.router)
html_router.include_router(storage.router)
html_router.include_router(analytics.router)
html_router.include_router(notifications.router)
html_router.include_router(settings.router)
html_router.include_router(htmx.router)