"""HTML routes for the Settings page."""

from typing import Optional
import logging

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_current_user_optional
from app.html.deps import get_html_db
from app.html.i18n import get_request_locale, normalize_locale, translate
from app.html.templating import templates
from app.html.utils import require_active_user
from app.models.company import Company
from app.schemas.settings import (
    ARSettings,
    BackupSettings,
    GeneralSettings,
    NotificationSettings,
    SecuritySettings,
    StorageSettings,
)
from app.services.backup_service import BackupService
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)
router = APIRouter()


async def _yd_companies(db: AsyncSession) -> list[dict]:
    """Return companies that have a Yandex Disk token configured."""
    stmt = select(Company).where(
        Company.storage_provider == "yandex_disk",
        Company.yandex_disk_token.isnot(None),
    )
    result = await db.execute(stmt)
    return [{"id": company.id, "name": company.name} for company in result.scalars().all()]


async def _render_settings(
    request: Request,
    db: AsyncSession,
    current_user,
    active_section: str = "general",
    success_message: Optional[str] = None,
    error_message: Optional[str] = None,
) -> HTMLResponse:
    """Build the settings page response with fresh data from DB."""
    settings_service = SettingsService(db)
    locale = get_request_locale(request)
    try:
        all_settings = await settings_service.get_all_settings()
    except Exception as exc:
        logger.error("settings_load_failed: %s", exc)
        from app.html.mock import SETTINGS_MOCK_DATA

        all_settings = SETTINGS_MOCK_DATA["settings"]

    yd_company_list: list[dict] = []
    backup_history: list[dict] = []
    try:
        yd_company_list = await _yd_companies(db)
    except Exception:
        pass
    try:
        service = BackupService()
        records = await service.list_backups(db, limit=10)
        backup_history = [
            {
                "id": record.id,
                "started_at": record.started_at,
                "finished_at": record.finished_at,
                "status": record.status,
                "size_bytes": record.size_bytes,
                "yd_path": record.yd_path,
                "error_message": record.error_message,
                "trigger": record.trigger,
            }
            for record in records
        ]
    except Exception:
        pass

    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "settings": all_settings,
            "current_user": current_user,
            "active_section": active_section,
            "success_message": success_message,
            "error_message": error_message,
            "yd_companies": yd_company_list,
            "backup_history": backup_history,
            "active_locale": locale,
        },
    )


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db),
):
    """Render the settings page."""
    redirect = require_active_user(current_user)
    if redirect:
        return redirect
    return await _render_settings(request, db, current_user)


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
    language: str = Form("ru"),
    default_subscription_years: int = Form(30),
):
    """Save general settings."""
    redirect = require_active_user(current_user)
    if redirect:
        return redirect

    settings_service = SettingsService(db)
    try:
        normalized_language = normalize_locale(language)
        await settings_service.update_general_settings(
            GeneralSettings(
                site_title=site_title,
                admin_email=admin_email,
                site_description=site_description,
                maintenance_mode=(maintenance_mode == "on"),
                timezone=timezone,
                language=normalized_language,
                default_subscription_years=default_subscription_years,
            )
        )
        request.session["language"] = normalized_language
        request.state.locale = normalized_language
        return await _render_settings(
            request,
            db,
            current_user,
            active_section="general",
            success_message=translate("settings.saved_general", normalized_language),
        )
    except Exception as exc:
        logger.error("general_settings_update_failed: %s", exc)
        return await _render_settings(
            request,
            db,
            current_user,
            active_section="general",
            error_message=translate("settings.save_failed", get_request_locale(request)),
        )


@router.post("/settings/security")
async def update_security_settings(
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db),
    password_min_length: int = Form(...),
    session_timeout: int = Form(...),
    require_2fa: str = Form("off"),
    telegram_2fa_chat_id: str = Form(""),
    max_login_attempts: int = Form(5),
    lockout_duration: int = Form(300),
    api_rate_limit: int = Form(100),
):
    """Save security settings."""
    redirect = require_active_user(current_user)
    if redirect:
        return redirect

    settings_service = SettingsService(db)
    try:
        normalized_2fa_chat_id = telegram_2fa_chat_id.strip() or None
        if require_2fa == "on" and not normalized_2fa_chat_id:
            return await _render_settings(
                request,
                db,
                current_user,
                active_section="security",
                error_message=translate("auth.enable_2fa_chat_required", get_request_locale(request)),
            )

        await settings_service.update_security_settings(
            SecuritySettings(
                password_min_length=password_min_length,
                session_timeout=session_timeout,
                require_2fa=(require_2fa == "on"),
                telegram_2fa_chat_id=normalized_2fa_chat_id,
                max_login_attempts=max_login_attempts,
                lockout_duration=lockout_duration,
                api_rate_limit=api_rate_limit,
            )
        )
        return await _render_settings(
            request,
            db,
            current_user,
            active_section="security",
            success_message=translate("settings.saved_security", get_request_locale(request)),
        )
    except Exception as exc:
        logger.error("security_settings_update_failed: %s", exc)
        return await _render_settings(
            request,
            db,
            current_user,
            active_section="security",
            error_message=translate("settings.save_failed", get_request_locale(request)),
        )


@router.post("/settings/ar")
async def update_ar_settings(
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db),
    marker_generation_enabled: str = Form("on"),
    thumbnail_quality: int = Form(80),
    video_processing_enabled: str = Form("on"),
    default_ar_viewer_theme: str = Form("default"),
    default_content_lifetime_years: int = Form(30),
):
    """Save AR content settings."""
    redirect = require_active_user(current_user)
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
                default_content_lifetime_years=max(1, default_content_lifetime_years),
            )
        )
        return await _render_settings(
            request,
            db,
            current_user,
            active_section="ar",
            success_message=translate("settings.saved_ar", get_request_locale(request)),
        )
    except Exception as exc:
        logger.error("ar_settings_update_failed: %s", exc)
        return await _render_settings(
            request,
            db,
            current_user,
            active_section="ar",
            error_message=translate("settings.save_failed", get_request_locale(request)),
        )


_SCHEDULE_CRON_MAP = {
    "daily": "0 3 * * *",
    "twice_daily": "0 3,15 * * *",
    "weekly": "0 3 * * 1",
}


@router.post("/settings/backup")
async def update_backup_settings(
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db),
    backup_enabled: str = Form("off"),
    backup_company_id: int = Form(0),
    backup_yd_folder: str = Form("backups"),
    backup_schedule: str = Form("daily"),
    backup_cron: str = Form("0 3 * * *"),
    backup_retention_days: int = Form(30),
    backup_max_copies: int = Form(30),
):
    """Save backup settings and reschedule the APScheduler job."""
    redirect = require_active_user(current_user)
    if redirect:
        return redirect

    is_enabled = backup_enabled == "on"
    effective_cron = _SCHEDULE_CRON_MAP.get(backup_schedule, "0 3 * * *") if backup_schedule != "custom" else backup_cron
    settings_service = SettingsService(db)

    try:
        await settings_service.update_backup_settings(
            BackupSettings(
                backup_enabled=is_enabled,
                backup_company_id=backup_company_id or None,
                backup_yd_folder=backup_yd_folder.strip("/") or "backups",
                backup_schedule=backup_schedule,
                backup_cron=effective_cron,
                backup_retention_days=max(1, backup_retention_days),
                backup_max_copies=max(1, backup_max_copies),
            )
        )

        from app.core.scheduler import reschedule_backup

        reschedule_backup(effective_cron, enabled=is_enabled and bool(backup_company_id))

        return await _render_settings(
            request,
            db,
            current_user,
            active_section="backup",
            success_message=translate("settings.saved_backup", get_request_locale(request)),
        )
    except Exception as exc:
        logger.error("backup_settings_update_failed: %s", exc)
        return await _render_settings(
            request,
            db,
            current_user,
            active_section="backup",
            error_message=translate("settings.save_failed_backup", get_request_locale(request)),
        )


@router.post("/settings/notifications")
async def update_notification_settings(
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db),
    email_enabled: str = Form("off"),
    smtp_host: str = Form(""),
    smtp_port: int = Form(587),
    smtp_username: str = Form(""),
    smtp_password: str = Form(""),
    smtp_from_email: str = Form("noreply@vertexar.com"),
    telegram_enabled: str = Form("off"),
    telegram_bot_token: str = Form(""),
    telegram_admin_chat_id: str = Form(""),
    telegram_alerts_enabled: str = Form("off"),
    alert_on_critical: str = Form("off"),
    alert_on_warning: str = Form("off"),
    alert_on_backup_failed: str = Form("off"),
    alert_on_storage_failed: str = Form("off"),
    alert_on_health_degraded: str = Form("off"),
):
    """Save notification settings."""
    redirect = require_active_user(current_user)
    if redirect:
        return redirect

    settings_service = SettingsService(db)
    try:
        current = await settings_service.get_all_settings()
        effective_smtp_password = smtp_password if smtp_password.strip() else current.notifications.smtp_password

        await settings_service.update_notification_settings(
            NotificationSettings(
                email_enabled=(email_enabled == "on"),
                smtp_host=smtp_host.strip() or None,
                smtp_port=smtp_port,
                smtp_username=smtp_username.strip() or None,
                smtp_password=effective_smtp_password,
                smtp_from_email=smtp_from_email.strip(),
                telegram_enabled=(telegram_enabled == "on"),
                telegram_bot_token=telegram_bot_token.strip() or None,
                telegram_admin_chat_id=telegram_admin_chat_id.strip() or None,
                telegram_alerts_enabled=(telegram_alerts_enabled == "on"),
                alert_on_critical=(alert_on_critical == "on"),
                alert_on_warning=(alert_on_warning == "on"),
                alert_on_backup_failed=(alert_on_backup_failed == "on"),
                alert_on_storage_failed=(alert_on_storage_failed == "on"),
                alert_on_health_degraded=(alert_on_health_degraded == "on"),
            )
        )
        return await _render_settings(
            request,
            db,
            current_user,
            active_section="notifications",
            success_message=translate("settings.saved_notifications", get_request_locale(request)),
        )
    except Exception as exc:
        logger.error("notification_settings_update_failed: %s", exc)
        return await _render_settings(
            request,
            db,
            current_user,
            active_section="notifications",
            error_message=translate("settings.save_failed", get_request_locale(request)),
        )


@router.post("/settings/storage")
async def update_storage_settings(
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db),
    default_storage: str = Form("local"),
    max_file_size: int = Form(100),
    cdn_enabled: str = Form("off"),
    cdn_url: str = Form(""),
):
    """Save storage settings."""
    redirect = require_active_user(current_user)
    if redirect:
        return redirect

    settings_service = SettingsService(db)
    try:
        current = await settings_service.get_all_settings()
        await settings_service.update_storage_settings(
            StorageSettings(
                default_storage=default_storage,
                max_file_size=max(1, max_file_size),
                cdn_enabled=(cdn_enabled == "on"),
                cdn_url=cdn_url.strip() or None,
                backup_enabled=current.storage.backup_enabled,
                backup_retention_days=current.storage.backup_retention_days,
            )
        )
        return await _render_settings(
            request,
            db,
            current_user,
            active_section="storage",
            success_message=translate("settings.saved_storage", get_request_locale(request)),
        )
    except Exception as exc:
        logger.error("storage_settings_update_failed: %s", exc)
        return await _render_settings(
            request,
            db,
            current_user,
            active_section="storage",
            error_message=translate("settings.save_failed", get_request_locale(request)),
        )
