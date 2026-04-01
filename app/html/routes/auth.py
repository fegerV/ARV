from datetime import datetime, timedelta, timezone
import json
import secrets
import uuid

import structlog
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import (
    LOCKOUT_DURATION,
    MAX_LOGIN_ATTEMPTS,
    create_access_token,
    create_access_token_cookie,
    get_current_user_optional,
    get_session_timeout_minutes,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.redis import redis_client
from app.core.security import get_password_hash, needs_password_rehash, verify_password
from app.html.i18n import normalize_locale, translate
from app.html.templating import templates
from app.middleware.rate_limiter import limiter
from app.models.user import User

router = APIRouter()
logger = structlog.get_logger()


def _login_context(request: Request, **extra) -> dict:
    context = {
        "request": request,
        "error": None,
        "locked_until": None,
        "attempts_left": None,
    }
    context.update(extra)
    return context


def _render_login(request: Request, **extra) -> HTMLResponse:
    return templates.TemplateResponse("admin/login.html", _login_context(request, **extra))


def _render_2fa_step(request: Request, pending_2fa_token: str, error: str | None = None) -> HTMLResponse:
    return _render_login(
        request,
        error=error,
        step_2fa=True,
        pending_2fa_token=pending_2fa_token,
    )


async def _get_html_session_timeout_minutes(db: AsyncSession) -> int:
    try:
        return await get_session_timeout_minutes(db)
    except Exception:
        return getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60)


@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Admin login page."""
    limiter.limit("5/minute")
    return _render_login(request)


@router.post("/admin/language", response_class=RedirectResponse)
async def admin_set_language(request: Request, language: str = Form(...)):
    """Persist selected admin locale in session and redirect back."""
    request.session["language"] = normalize_locale(language)
    redirect_to = request.headers.get("referer") or "/admin"
    return RedirectResponse(url=redirect_to, status_code=303)


@router.get("/admin/login-form", response_class=RedirectResponse)
async def login_form_get():
    """Redirect legacy GET login form URL to login page."""
    return RedirectResponse(url="/admin/login", status_code=302)


@router.post("/admin/login-form", response_class=HTMLResponse)
async def login_form(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Handle form-based login for the HTML interface."""
    try:
        result = await db.execute(select(User).where(User.email == username))
        user = result.scalar_one_or_none()
    except Exception as exc:
        logger.exception("login_form_error", error=str(exc))
        return _render_login(
            request,
            error=translate("auth.error_login", request.state.locale, error=str(exc)),
        )

    if user and user.locked_until:
        if datetime.now(timezone.utc) < user.locked_until:
            logger.warning("login_attempt_locked_account", email=username)
            return _render_login(
                request,
                error=translate("auth.account_locked", request.state.locale),
                locked_until=user.locked_until.isoformat(),
            )
        user.locked_until = None
        user.login_attempts = 0
        await db.commit()

    if not user or not verify_password(password, user.hashed_password):
        logger.warning("login_failed", email=username)
        if user:
            user.login_attempts = (user.login_attempts or 0) + 1
            if user.login_attempts >= MAX_LOGIN_ATTEMPTS:
                user.locked_until = datetime.now(timezone.utc) + LOCKOUT_DURATION
                await db.commit()
                return _render_login(
                    request,
                    error=translate(
                        "auth.too_many_attempts",
                        request.state.locale,
                        minutes=LOCKOUT_DURATION.seconds // 60,
                    ),
                    locked_until=user.locked_until.isoformat(),
                )

            await db.commit()
            attempts_left = max(MAX_LOGIN_ATTEMPTS - user.login_attempts, 0)
            return _render_login(
                request,
                error=translate("auth.invalid_credentials", request.state.locale),
                attempts_left=attempts_left,
            )
        return _render_login(request, error=translate("auth.invalid_credentials", request.state.locale))

    if not user.is_active:
        return _render_login(request, error=translate("auth.account_disabled", request.state.locale))

    try:
        if needs_password_rehash(user.hashed_password):
            user.hashed_password = get_password_hash(password)

        user.login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.now(timezone.utc)
        await db.commit()

        from app.services.settings_service import SettingsService

        all_settings = None
        try:
            settings_service = SettingsService(db)
            all_settings = await settings_service.get_all_settings()
            timeout_minutes = await _get_html_session_timeout_minutes(db)
        except Exception:
            timeout_minutes = getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60)

        if all_settings and getattr(all_settings.security, "require_2fa", False):
            code = f"{secrets.randbelow(10**6):06d}"
            pending_token = str(uuid.uuid4())
            redis_key = f"2fa:pending:{pending_token}"
            await redis_client.set(
                redis_key,
                json.dumps({"user_id": user.id, "email": user.email, "code": code}),
                ex=300,
            )
            chat_id = (getattr(all_settings.security, "telegram_2fa_chat_id", None) or "455847500").strip()
            bot_token = getattr(all_settings.notifications, "telegram_bot_token", None) or settings.TELEGRAM_BOT_TOKEN
            if bot_token and chat_id:
                try:
                    import httpx

                    async with httpx.AsyncClient() as client:
                        await client.post(
                            f"https://api.telegram.org/bot{bot_token}/sendMessage",
                            json={
                                "chat_id": chat_id,
                                "text": f"Код для входа в Vertex AR Admin: {code}\nДействует 5 минут.",
                                "disable_web_page_preview": True,
                            },
                            timeout=10.0,
                        )
                except Exception as send_err:
                    logger.warning("2fa_telegram_send_failed", error=str(send_err))
            return _render_2fa_step(request, pending_token)

        access_token = create_access_token(
            data={"sub": user.email, "user_id": user.id},
            expires_delta=timedelta(minutes=timeout_minutes),
        )

        logger.info("user_login_successful", user_id=user.id, email=user.email)
        response = RedirectResponse(url="/admin", status_code=303)
        create_access_token_cookie(response, access_token, timeout_minutes)
        return response
    except Exception as exc:
        logger.exception("login_form_success_error", error=str(exc))
        return _render_login(
            request,
            error=translate("auth.error_login_process", request.state.locale, error=str(exc)),
        )


@router.post("/admin/login-2fa", response_class=HTMLResponse)
async def login_2fa_verify(
    request: Request,
    pending_2fa_token: str = Form(...),
    code: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Verify 2FA code and create browser session."""
    code = (code or "").strip().replace(" ", "")
    if len(code) != 6 or not code.isdigit():
        return _render_2fa_step(request, pending_2fa_token, error=translate("auth.enter_2fa_code", request.state.locale))

    redis_key = f"2fa:pending:{pending_2fa_token}"
    try:
        raw = await redis_client.get(redis_key)
    except Exception as exc:
        logger.warning("2fa_redis_get_error", error=str(exc))
        return _render_login(request, error=translate("auth.otp_verify_error", request.state.locale))

    if not raw:
        return _render_login(request, error=translate("auth.otp_expired", request.state.locale))

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        await redis_client.delete(redis_key)
        return _render_login(request, error=translate("auth.otp_data_error", request.state.locale))

    if data.get("code") != code:
        return _render_2fa_step(request, pending_2fa_token, error=translate("auth.otp_invalid", request.state.locale))

    user_id = data.get("user_id")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        await redis_client.delete(redis_key)
        return _render_login(request, error=translate("auth.user_not_found_or_blocked", request.state.locale))

    await redis_client.delete(redis_key)
    timeout_minutes = await _get_html_session_timeout_minutes(db)

    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=timedelta(minutes=timeout_minutes),
    )
    logger.info("user_login_successful_2fa", user_id=user.id, email=user.email)

    response = RedirectResponse(url="/admin", status_code=303)
    create_access_token_cookie(response, access_token, timeout_minutes)
    return response


@router.post("/admin/logout", response_class=RedirectResponse)
async def admin_logout(request: Request):
    """Browser logout endpoint used by the admin header."""
    from app.api.routes.auth import clear_auth_cookies

    response = RedirectResponse(url="/admin/login", status_code=303)
    clear_auth_cookies(response)
    request.session.pop("language", None)
    return response


@router.get("/", response_class=HTMLResponse)
async def root(request: Request, current_user=Depends(get_current_user_optional)):
    """Root endpoint redirects authenticated users to admin."""
    if current_user and current_user.is_active:
        return RedirectResponse("/admin")
    return templates.TemplateResponse("landing.html", {"request": request})
