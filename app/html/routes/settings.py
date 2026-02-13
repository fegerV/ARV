"""HTML routes for the Settings page.

Kept sections: general, security, ar.
Removed (not wired to business logic): storage, notifications, api, integrations.
"""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_current_user_optional
from app.html.deps import get_html_db
from app.html.filters import datetime_format
from app.schemas.settings import ARSettings, GeneralSettings, SecuritySettings
from app.services.settings_service import SettingsService

import logging

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")
templates.env.filters["datetime_format"] = datetime_format


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_active_user(current_user) -> RedirectResponse | None:
    """Return a redirect if the user is missing or inactive, else ``None``."""
    if not current_user or not current_user.is_active:
        return RedirectResponse(url="/admin/login", status_code=303)
    return None


async def _render_settings(
    request: Request,
    db: AsyncSession,
    current_user,
    active_section: str = "general",
    success_message: str | None = None,
    error_message: str | None = None,
) -> HTMLResponse:
    """Build the settings page response with fresh data from DB."""
    settings_service = SettingsService(db)
    try:
        all_settings = await settings_service.get_all_settings()
    except Exception as exc:
        logger.error("Error loading settings: %s", exc)
        from app.html.mock import SETTINGS_MOCK_DATA
        all_settings = SETTINGS_MOCK_DATA["settings"]

    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "settings": all_settings,
            "current_user": current_user,
            "active_section": active_section,
            "success_message": success_message,
            "error_message": error_message,
        },
    )


# ---------------------------------------------------------------------------
# GET  /settings
# ---------------------------------------------------------------------------

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db),
):
    """Render the settings page."""
    redirect = _require_active_user(current_user)
    if redirect:
        return redirect
    return await _render_settings(request, db, current_user)


# ---------------------------------------------------------------------------
# POST  /settings/general
# ---------------------------------------------------------------------------

@router.post("/settings/general")
async def update_general_settings(
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db),
    site_title: str = Form(...),
    admin_email: str = Form(...),
    site_description: str = Form(...),
    maintenance_mode: str = Form("off"),
    timezone: str = Form("UTC"),
    language: str = Form("en"),
    default_subscription_years: int = Form(1),
):
    """Save general settings."""
    redirect = _require_active_user(current_user)
    if redirect:
        return redirect

    settings_service = SettingsService(db)
    try:
        await settings_service.update_general_settings(
            GeneralSettings(
                site_title=site_title,
                admin_email=admin_email,
                site_description=site_description,
                maintenance_mode=(maintenance_mode == "on"),
                timezone=timezone,
                language=language,
                default_subscription_years=default_subscription_years,
            )
        )
        return await _render_settings(
            request, db, current_user,
            active_section="general",
            success_message="Основные настройки сохранены",
        )
    except Exception as exc:
        logger.error("Error updating general settings: %s", exc)
        return await _render_settings(
            request, db, current_user,
            active_section="general",
            error_message="Не удалось сохранить настройки",
        )


# ---------------------------------------------------------------------------
# POST  /settings/security
# ---------------------------------------------------------------------------

@router.post("/settings/security")
async def update_security_settings(
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db),
    password_min_length: int = Form(...),
    session_timeout: int = Form(...),
    require_2fa: str = Form("off"),
    max_login_attempts: int = Form(5),
    lockout_duration: int = Form(300),
    api_rate_limit: int = Form(100),
):
    """Save security settings."""
    redirect = _require_active_user(current_user)
    if redirect:
        return redirect

    settings_service = SettingsService(db)
    try:
        await settings_service.update_security_settings(
            SecuritySettings(
                password_min_length=password_min_length,
                session_timeout=session_timeout,
                require_2fa=(require_2fa == "on"),
                max_login_attempts=max_login_attempts,
                lockout_duration=lockout_duration,
                api_rate_limit=api_rate_limit,
            )
        )
        return await _render_settings(
            request, db, current_user,
            active_section="security",
            success_message="Настройки безопасности сохранены",
        )
    except Exception as exc:
        logger.error("Error updating security settings: %s", exc)
        return await _render_settings(
            request, db, current_user,
            active_section="security",
            error_message="Не удалось сохранить настройки",
        )


# ---------------------------------------------------------------------------
# POST  /settings/ar
# ---------------------------------------------------------------------------

@router.post("/settings/ar")
async def update_ar_settings(
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db),
    marker_generation_enabled: str = Form("on"),
    thumbnail_quality: int = Form(80),
    video_processing_enabled: str = Form("on"),
    default_ar_viewer_theme: str = Form("default"),
    qr_code_expiration_days: int = Form(365),
):
    """Save AR content settings. MindAR max-features preserved from DB."""
    redirect = _require_active_user(current_user)
    if redirect:
        return redirect

    settings_service = SettingsService(db)
    try:
        current = await settings_service.get_all_settings()
        mindar_max_features = getattr(current.ar, "mindar_max_features", 1000)

        await settings_service.update_ar_settings(
            ARSettings(
                mindar_max_features=mindar_max_features,
                marker_generation_enabled=(marker_generation_enabled == "on"),
                thumbnail_quality=thumbnail_quality,
                video_processing_enabled=(video_processing_enabled == "on"),
                default_ar_viewer_theme=default_ar_viewer_theme,
                qr_code_expiration_days=qr_code_expiration_days,
            )
        )
        return await _render_settings(
            request, db, current_user,
            active_section="ar",
            success_message="Настройки AR-контента сохранены",
        )
    except Exception as exc:
        logger.error("Error updating AR settings: %s", exc)
        return await _render_settings(
            request, db, current_user,
            active_section="ar",
            error_message="Не удалось сохранить настройки",
        )
