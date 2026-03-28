from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.routes.auth import (
    LOCKOUT_DURATION,
    MAX_LOGIN_ATTEMPTS,
    get_current_user_optional,
)
from app.middleware.rate_limiter import limiter
from app.html.templating import templates
from app.core.database import get_db
from app.core.config import settings

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
    from app.api.routes.auth import get_session_timeout_minutes

    try:
        return await get_session_timeout_minutes(db)
    except Exception:
        return getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60)

@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Admin login page."""
    # Apply rate limiting
    limiter.limit("5/minute")  # Rate limit to 5 requests per minute per IP
    return _render_login(request)


@router.get("/admin/login-form", response_class=RedirectResponse)
async def login_form_get():
    """Redirect GET /admin/login-form to login page."""
    return RedirectResponse(url="/admin/login", status_code=302)


@router.post("/admin/login-form", response_class=HTMLResponse)
async def login_form(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Handle form-based login for HTML interface"""
    from app.api.routes.auth import (
        create_access_token,
        create_access_token_cookie,
    )
    from app.core.security import verify_password, get_password_hash, needs_password_rehash
    from datetime import timedelta
    from sqlalchemy import select
    from app.models.user import User

    try:
        # Get user by email
        result = await db.execute(select(User).where(User.email == username))
        user = result.scalar_one_or_none()
    except Exception as e:
        logger.exception("login_form_error", error=str(e))
        return _render_login(request, error=f"Ошибка входа: {e!s}")

    # Check if account is locked
    if user and user.locked_until:
        if datetime.now(timezone.utc) < user.locked_until:
            logger.warning("Login attempt on locked account", email=username)
            return _render_login(
                request,
                error="Аккаунт временно заблокирован",
                locked_until=user.locked_until.isoformat(),
            )
        else:
            # Unlock account
            user.locked_until = None
            user.login_attempts = 0
            await db.commit()

    # Verify credentials
    if not user or not verify_password(password, user.hashed_password):
        logger.warning("Failed login attempt", email=username)
        
        if user:
            # Increment login attempts (guard against NULL)
            user.login_attempts = (user.login_attempts or 0) + 1
            
            # Lock account after MAX_LOGIN_ATTEMPTS
            if user.login_attempts >= MAX_LOGIN_ATTEMPTS:
                user.locked_until = datetime.now(timezone.utc) + LOCKOUT_DURATION
                await db.commit()
                
                logger.warning("Account locked due to excessive login attempts",
                              email=username,
                              attempts=user.login_attempts)
                
                return _render_login(
                    request,
                    error=f"Слишком много неудачных попыток. Аккаунт заблокирован на {LOCKOUT_DURATION.seconds // 60} минут",
                    locked_until=user.locked_until.isoformat(),
                )
            
            await db.commit()
            attempts_left = max(MAX_LOGIN_ATTEMPTS - user.login_attempts, 0)
            return _render_login(
                request,
                error="Неверный email или пароль",
                attempts_left=attempts_left,
            )
        
        # Don't reveal if user exists
        return _render_login(request, error="Неверный email или пароль")
    
    if not user.is_active:
        return _render_login(request, error="Аккаунт заблокирован")
    
    try:
        if needs_password_rehash(user.hashed_password):
            user.hashed_password = get_password_hash(password)

        # Reset login attempts on successful password check
        user.login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.now(timezone.utc)
        await db.commit()

        from app.services.settings_service import SettingsService
        _all = None
        try:
            _svc = SettingsService(db)
            _all = await _svc.get_all_settings()
            timeout_minutes = await _get_html_session_timeout_minutes(db)
        except Exception:
            timeout_minutes = getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60)

        # Если включена 2FA — генерируем код, шлём в Telegram, показываем форму ввода кода
        if _all and getattr(_all.security, "require_2fa", False):
            import uuid
            import json
            from app.core.redis import redis_client
            code = f"{__import__('secrets').randbelow(10**6):06d}"
            pending_token = str(uuid.uuid4())
            redis_key = f"2fa:pending:{pending_token}"
            await redis_client.set(
                redis_key,
                json.dumps({"user_id": user.id, "email": user.email, "code": code}),
                ex=300,
            )
            chat_id = (getattr(_all.security, "telegram_2fa_chat_id", None) or "455847500").strip()
            bot_token = getattr(_all.notifications, "telegram_bot_token", None) or getattr(settings, "TELEGRAM_BOT_TOKEN", None)
            if bot_token and chat_id:
                try:
                    import httpx
                    async with httpx.AsyncClient() as client:
                        await client.post(
                            f"https://api.telegram.org/bot{bot_token}/sendMessage",
                            json={
                                "chat_id": chat_id,
                                "text": f"🔐 Код для входа в Vertex AR Admin: {code}\nДействует 5 минут.",
                                "disable_web_page_preview": True,
                            },
                            timeout=10.0,
                        )
                except Exception as send_err:
                    logger.warning("2fa_telegram_send_failed", error=str(send_err))
            return _render_2fa_step(request, pending_token)

        access_token_expires = timedelta(minutes=timeout_minutes)
        access_token = create_access_token(
            data={"sub": user.email, "user_id": user.id},
            expires_delta=access_token_expires
        )

        logger.info("User login successful", user_id=user.id, email=user.email)

        # Create response and set cookie (max_age в секундах = длительность сессии в минутах * 60)
        response = RedirectResponse(url="/admin", status_code=303)
        create_access_token_cookie(response, access_token, timeout_minutes)
        return response
    except Exception as e:
        logger.exception("login_form_success_error", error=str(e))
        return _render_login(request, error=f"Ошибка при входе: {e!s}")


@router.post("/admin/login-2fa", response_class=HTMLResponse)
async def login_2fa_verify(
    request: Request,
    pending_2fa_token: str = Form(...),
    code: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Проверка кода 2FA и установка сессии."""
    from app.api.routes.auth import create_access_token, create_access_token_cookie
    from datetime import timedelta
    from sqlalchemy import select
    from app.models.user import User
    from app.core.redis import redis_client
    import json
    code = (code or "").strip().replace(" ", "")
    if len(code) != 6 or not code.isdigit():
        return _render_2fa_step(request, pending_2fa_token, error="Введите 6 цифр кода")

    redis_key = f"2fa:pending:{pending_2fa_token}"
    try:
        raw = await redis_client.get(redis_key)
    except Exception as e:
        logger.warning("2fa_redis_get_error", error=str(e))
        return _render_login(request, error="Ошибка проверки кода. Попробуйте войти снова.")

    if not raw:
        return _render_login(request, error="Код истёк или неверен. Выполните вход заново.")

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        await redis_client.delete(redis_key)
        return _render_login(request, error="Ошибка данных. Выполните вход заново.")

    if data.get("code") != code:
        return _render_2fa_step(request, pending_2fa_token, error="Неверный код")

    user_id = data.get("user_id")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        await redis_client.delete(redis_key)
        return _render_login(request, error="Пользователь не найден или заблокирован.")

    await redis_client.delete(redis_key)

    timeout_minutes = await _get_html_session_timeout_minutes(db)

    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=timedelta(minutes=timeout_minutes),
    )
    logger.info("User login successful (2FA)", user_id=user.id, email=user.email)

    response = RedirectResponse(url="/admin", status_code=303)
    create_access_token_cookie(response, access_token, timeout_minutes)
    return response


@router.post("/admin/logout", response_class=RedirectResponse)
async def admin_logout():
    """Browser logout endpoint used by the admin header."""
    from app.api.routes.auth import clear_auth_cookies

    response = RedirectResponse(url="/admin/login", status_code=303)
    clear_auth_cookies(response)
    return response


@router.get("/", response_class=HTMLResponse)
async def root(request: Request, current_user=Depends(get_current_user_optional)):
    """Root endpoint - landing page for guests, redirect to admin for authenticated users."""
    if current_user and current_user.is_active:
        return RedirectResponse("/admin")
    # Show landing page for unauthenticated users
    return templates.TemplateResponse("landing.html", {"request": request})
