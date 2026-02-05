from fastapi import APIRouter, Depends, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from app.html.deps import get_html_db
from app.api.routes.auth import get_current_user_optional
from app.services.settings_service import SettingsService
from app.schemas.settings import (
    AllSettings, GeneralSettings, SecuritySettings, StorageSettings,
    NotificationSettings, APISettings, IntegrationSettings, ARSettings
)
from app.html.filters import datetime_format
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")
templates.env.filters["datetime_format"] = datetime_format

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db)
):
    """Settings page."""
    if not current_user:
        # Redirect to login page if user is not authenticated
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        # Redirect to login page if user is not active
        return RedirectResponse(url="/admin/login", status_code=303)
    settings_service = SettingsService(db)
    
    try:
        all_settings = await settings_service.get_all_settings()
        
        context = {
            "request": request,
            "settings": all_settings,
            "current_user": current_user,
            "active_section": "general"
        }
        return templates.TemplateResponse("settings.html", context)
    except Exception as e:
        logger.error(f"Error loading settings page: {e}")
        # Fallback to mock data if database is not ready
        from app.html.mock import SETTINGS_MOCK_DATA
        context = {
            "request": request,
            "settings": SETTINGS_MOCK_DATA["settings"],
            "current_user": current_user,
            "active_section": "general"
        }
        return templates.TemplateResponse("settings.html", context)

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
    default_subscription_years: int = Form(1)
):
    """Update general settings."""
    if not current_user:
        # Redirect to login page if user is not authenticated
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        # Redirect to login page if user is not active
        return RedirectResponse(url="/admin/login", status_code=303)
    settings_service = SettingsService(db)
    
    try:
        general_settings = GeneralSettings(
            site_title=site_title,
            admin_email=admin_email,
            site_description=site_description,
            maintenance_mode=(maintenance_mode == "on"),
            timezone=timezone,
            language=language,
            default_subscription_years=default_subscription_years
        )
        
        await settings_service.update_general_settings(general_settings)
        
        # Return updated settings
        all_settings = await settings_service.get_all_settings()
        
        context = {
            "request": request,
            "settings": all_settings,
            "current_user": current_user,
            "active_section": "general",
            "success_message": "General settings updated successfully"
        }
        return templates.TemplateResponse("settings.html", context)
        
    except Exception as e:
        logger.error(f"Error updating general settings: {e}")
        
        # Return with error message
        all_settings = await settings_service.get_all_settings()
        context = {
            "request": request,
            "settings": all_settings,
            "current_user": current_user,
            "active_section": "general",
            "error_message": "Failed to update general settings"
        }
        return templates.TemplateResponse("settings.html", context)

@router.post("/settings/security")
async def update_security_settings(
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db),
    password_min_length: int = Form(...),
    session_timeout: int = Form(...),
    require_2fa: str = Form("off"),
    max_login_attempts: int = Form(5),
    lockout_duration: int = Form(30),
    api_rate_limit: int = Form(100)
):
    """Update security settings."""
    if not current_user:
        # Redirect to login page if user is not authenticated
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        # Redirect to login page if user is not active
        return RedirectResponse(url="/admin/login", status_code=303)
    settings_service = SettingsService(db)
    
    try:
        security_settings = SecuritySettings(
            password_min_length=password_min_length,
            session_timeout=session_timeout,
            require_2fa=(require_2fa == "on"),
            max_login_attempts=max_login_attempts,
            lockout_duration=lockout_duration,
            api_rate_limit=api_rate_limit
        )
        
        await settings_service.update_security_settings(security_settings)
        
        # Return updated settings
        all_settings = await settings_service.get_all_settings()
        
        context = {
            "request": request,
            "settings": all_settings,
            "current_user": current_user,
            "active_section": "security",
            "success_message": "Security settings updated successfully"
        }
        return templates.TemplateResponse("settings.html", context)
        
    except Exception as e:
        logger.error(f"Error updating security settings: {e}")
        
        # Return with error message
        all_settings = await settings_service.get_all_settings()
        context = {
            "request": request,
            "settings": all_settings,
            "current_user": current_user,
            "active_section": "security",
            "error_message": "Failed to update security settings"
        }
        return templates.TemplateResponse("settings.html", context)

@router.post("/settings/storage")
async def update_storage_settings(
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db),
    default_storage: str = Form(...),
    max_file_size: int = Form(...),
    cdn_enabled: str = Form("off"),
    cdn_url: str = Form(""),
    backup_enabled: str = Form("on"),
    backup_retention_days: int = Form(30)
):
    """Update storage settings."""
    if not current_user:
        # Redirect to login page if user is not authenticated
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        # Redirect to login page if user is not active
        return RedirectResponse(url="/admin/login", status_code=303)
    settings_service = SettingsService(db)
    
    try:
        storage_settings = StorageSettings(
            default_storage=default_storage,
            max_file_size=max_file_size,
            cdn_enabled=(cdn_enabled == "on"),
            cdn_url=cdn_url if cdn_url else None,
            backup_enabled=(backup_enabled == "on"),
            backup_retention_days=backup_retention_days
        )
        
        await settings_service.update_storage_settings(storage_settings)
        
        # Return updated settings
        all_settings = await settings_service.get_all_settings()
        
        context = {
            "request": request,
            "settings": all_settings,
            "current_user": current_user,
            "active_section": "storage",
            "success_message": "Storage settings updated successfully"
        }
        return templates.TemplateResponse("settings.html", context)
        
    except Exception as e:
        logger.error(f"Error updating storage settings: {e}")
        
        # Return with error message
        all_settings = await settings_service.get_all_settings()
        context = {
            "request": request,
            "settings": all_settings,
            "current_user": current_user,
            "active_section": "storage",
            "error_message": "Failed to update storage settings"
        }
        return templates.TemplateResponse("settings.html", context)

@router.post("/settings/notifications")
async def update_notification_settings(
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db),
    email_enabled: str = Form("on"),
    smtp_host: str = Form(""),
    smtp_port: int = Form(587),
    smtp_username: str = Form(""),
    smtp_from_email: str = Form("noreply@vertexar.com"),
    telegram_enabled: str = Form("off"),
    telegram_bot_token: str = Form(""),
    telegram_admin_chat_id: str = Form("")
):
    """Update notification settings."""
    if not current_user:
        # Redirect to login page if user is not authenticated
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        # Redirect to login page if user is not active
        return RedirectResponse(url="/admin/login", status_code=303)
    settings_service = SettingsService(db)
    
    try:
        notification_settings = NotificationSettings(
            email_enabled=(email_enabled == "on"),
            smtp_host=smtp_host if smtp_host else None,
            smtp_port=smtp_port,
            smtp_username=smtp_username if smtp_username else None,
            smtp_from_email=smtp_from_email,
            telegram_enabled=(telegram_enabled == "on"),
            telegram_bot_token=telegram_bot_token if telegram_bot_token else None,
            telegram_admin_chat_id=telegram_admin_chat_id if telegram_admin_chat_id else None
        )
        
        await settings_service.update_notification_settings(notification_settings)
        
        # Return updated settings
        all_settings = await settings_service.get_all_settings()
        
        context = {
            "request": request,
            "settings": all_settings,
            "current_user": current_user,
            "active_section": "notifications",
            "success_message": "Notification settings updated successfully"
        }
        return templates.TemplateResponse("settings.html", context)
        
    except Exception as e:
        logger.error(f"Error updating notification settings: {e}")
        
        # Return with error message
        all_settings = await settings_service.get_all_settings()
        context = {
            "request": request,
            "settings": all_settings,
            "current_user": current_user,
            "active_section": "notifications",
            "error_message": "Failed to update notification settings"
        }
        return templates.TemplateResponse("settings.html", context)

@router.post("/settings/api")
async def update_api_settings(
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db),
    api_keys_enabled: str = Form("on"),
    webhook_enabled: str = Form("off"),
    webhook_url: str = Form(""),
    documentation_public: str = Form("on"),
    cors_origins: str = Form("http://localhost:3000,http://localhost:8000")
):
    """Update API settings."""
    if not current_user:
        # Redirect to login page if user is not authenticated
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        # Redirect to login page if user is not active
        return RedirectResponse(url="/admin/login", status_code=303)
    settings_service = SettingsService(db)
    
    try:
        # Parse CORS origins
        cors_list = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
        
        api_settings = APISettings(
            api_keys_enabled=(api_keys_enabled == "on"),
            webhook_enabled=(webhook_enabled == "on"),
            webhook_url=webhook_url if webhook_url else None,
            documentation_public=(documentation_public == "on"),
            cors_origins=cors_list
        )
        
        await settings_service.update_api_settings(api_settings)
        
        # Return updated settings
        all_settings = await settings_service.get_all_settings()
        
        context = {
            "request": request,
            "settings": all_settings,
            "current_user": current_user,
            "active_section": "api",
            "success_message": "API settings updated successfully"
        }
        return templates.TemplateResponse("settings.html", context)
        
    except Exception as e:
        logger.error(f"Error updating API settings: {e}")
        
        # Return with error message
        all_settings = await settings_service.get_all_settings()
        context = {
            "request": request,
            "settings": all_settings,
            "current_user": current_user,
            "active_section": "api",
            "error_message": "Failed to update API settings"
        }
        return templates.TemplateResponse("settings.html", context)

@router.post("/settings/integrations")
async def update_integration_settings(
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db),
    google_oauth_enabled: str = Form("off"),
    google_client_id: str = Form(""),
    payment_provider: str = Form("stripe"),
    stripe_public_key: str = Form(""),
    analytics_enabled: str = Form("off"),
    analytics_provider: str = Form("google")
):
    """Update integration settings."""
    if not current_user:
        # Redirect to login page if user is not authenticated
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        # Redirect to login page if user is not active
        return RedirectResponse(url="/admin/login", status_code=303)
    settings_service = SettingsService(db)
    
    try:
        integration_settings = IntegrationSettings(
            google_oauth_enabled=(google_oauth_enabled == "on"),
            google_client_id=google_client_id if google_client_id else None,
            payment_provider=payment_provider,
            stripe_public_key=stripe_public_key if stripe_public_key else None,
            analytics_enabled=(analytics_enabled == "on"),
            analytics_provider=analytics_provider
        )
        
        await settings_service.update_integration_settings(integration_settings)
        
        # Return updated settings
        all_settings = await settings_service.get_all_settings()
        
        context = {
            "request": request,
            "settings": all_settings,
            "current_user": current_user,
            "active_section": "integrations",
            "success_message": "Integration settings updated successfully"
        }
        return templates.TemplateResponse("settings.html", context)
        
    except Exception as e:
        logger.error(f"Error updating integration settings: {e}")
        
        # Return with error message
        all_settings = await settings_service.get_all_settings()
        context = {
            "request": request,
            "settings": all_settings,
            "current_user": current_user,
            "active_section": "integrations",
            "error_message": "Failed to update integration settings"
        }
        return templates.TemplateResponse("settings.html", context)

@router.post("/settings/ar")
async def update_ar_settings(
    request: Request,
    current_user=Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_html_db),
    marker_generation_enabled: str = Form("on"),
    thumbnail_quality: int = Form(80),
    video_processing_enabled: str = Form("on"),
    default_ar_viewer_theme: str = Form("default"),
    qr_code_expiration_days: int = Form(365)
):
    """Update AR settings. mindar_max_features removed (ARCore uses photo as marker)."""
    if not current_user:
        # Redirect to login page if user is not authenticated
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        # Redirect to login page if user is not active
        return RedirectResponse(url="/admin/login", status_code=303)
    settings_service = SettingsService(db)
    
    try:
        all_settings = await settings_service.get_all_settings()
        mindar_max_features = getattr(all_settings.ar, "mindar_max_features", 1000)
        ar_settings = ARSettings(
            mindar_max_features=mindar_max_features,
            marker_generation_enabled=(marker_generation_enabled == "on"),
            thumbnail_quality=thumbnail_quality,
            video_processing_enabled=(video_processing_enabled == "on"),
            default_ar_viewer_theme=default_ar_viewer_theme,
            qr_code_expiration_days=qr_code_expiration_days
        )
        
        await settings_service.update_ar_settings(ar_settings)
        
        # Return updated settings
        all_settings = await settings_service.get_all_settings()
        
        context = {
            "request": request,
            "settings": all_settings,
            "current_user": current_user,
            "active_section": "ar",
            "success_message": "AR settings updated successfully"
        }
        return templates.TemplateResponse("settings.html", context)
        
    except Exception as e:
        logger.error(f"Error updating AR settings: {e}")
        
        # Return with error message
        all_settings = await settings_service.get_all_settings()
        context = {
            "request": request,
            "settings": all_settings,
            "current_user": current_user,
            "active_section": "ar",
            "error_message": "Failed to update AR settings"
        }
        return templates.TemplateResponse("settings.html", context)