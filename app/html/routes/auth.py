from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.routes.auth import get_current_user_optional
from app.middleware.rate_limiter import limiter
from app.html.filters import datetime_format
from app.core.database import get_db
from app.core.config import settings

router = APIRouter()

templates = Jinja2Templates(directory="templates")
# Add datetime filter to templates
templates.env.filters["datetime_format"] = datetime_format

@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Admin login page."""
    # Apply rate limiting
    limiter.limit("5/minute")  # Rate limit to 5 requests per minute per IP
    
    context = {
        "request": request,
        "error": None,
        "locked_until": None,
        "attempts_left": None
    }
    return templates.TemplateResponse("admin/login.html", context)


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
    from app.api.routes.auth import verify_password, create_access_token
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from app.models.user import User
    import structlog

    logger = structlog.get_logger()

    try:
        # Get user by email
        result = await db.execute(select(User).where(User.email == username))
        user = result.scalar_one_or_none()
    except Exception as e:
        logger.exception("login_form_error", error=str(e))
        return templates.TemplateResponse(
            "admin/login.html",
            {"request": request, "error": f"Ошибка входа: {e!s}"},
        )

    # Check if account is locked
    if user and user.locked_until:
        if datetime.now(timezone.utc) < user.locked_until:
            logger.warning("Login attempt on locked account", email=username)
            # Return login page with error
            context = {
                "request": request,
                "error": "Аккаунт временно заблокирован",
                "locked_until": user.locked_until.isoformat()
            }
            return templates.TemplateResponse("admin/login.html", context)
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
            if user.login_attempts >= 5:
                from datetime import timedelta
                LOCKOUT_DURATION = timedelta(minutes=15)
                user.locked_until = datetime.now(timezone.utc) + LOCKOUT_DURATION
                await db.commit()
                
                logger.warning("Account locked due to excessive login attempts",
                              email=username,
                              attempts=user.login_attempts)
                
                context = {
                    "request": request,
                    "error": f"Слишком много неудачных попыток. Аккаунт заблокирован на {LOCKOUT_DURATION.seconds // 60} минут",
                    "locked_until": user.locked_until.isoformat()
                }
                return templates.TemplateResponse("admin/login.html", context)
            
            await db.commit()
            attempts_left = 5 - user.login_attempts
            
            context = {
                "request": request,
                "error": "Неверный email или пароль",
                "attempts_left": attempts_left
            }
            return templates.TemplateResponse("admin/login.html", context)
        
        # Don't reveal if user exists
        context = {
            "request": request,
            "error": "Неверный email или пароль"
        }
        return templates.TemplateResponse("admin/login.html", context)
    
    if not user.is_active:
        context = {
            "request": request,
            "error": "Аккаунт заблокирован"
        }
        return templates.TemplateResponse("admin/login.html", context)
    
    try:
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
            timeout_minutes = _all.security.session_timeout or settings.ACCESS_TOKEN_EXPIRE_MINUTES
        except Exception:
            timeout_minutes = getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60)

        # Если включена 2FA — генерируем код, шлём в Telegram, показываем форму ввода кода
        if getattr(_all.security, "require_2fa", False):
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
            return templates.TemplateResponse(
                "admin/login.html",
                {
                    "request": request,
                    "error": None,
                    "step_2fa": True,
                    "pending_2fa_token": pending_token,
                },
            )

        access_token_expires = timedelta(minutes=timeout_minutes)
        access_token = create_access_token(
            data={"sub": user.email, "user_id": user.id},
            expires_delta=access_token_expires
        )

        logger.info("User login successful", user_id=user.id, email=user.email)

        # Create response and set cookie (max_age в секундах = длительность сессии в минутах * 60)
        response = RedirectResponse(url="/admin", status_code=303)
        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=timeout_minutes * 60,
            path="/",
            secure=settings.is_production,
            httponly=True,
            samesite="lax",
        )
        return response
    except Exception as e:
        logger.exception("login_form_success_error", error=str(e))
        return templates.TemplateResponse(
            "admin/login.html",
            {"request": request, "error": f"Ошибка при входе: {e!s}"},
        )


@router.post("/admin/login-2fa", response_class=HTMLResponse)
async def login_2fa_verify(
    request: Request,
    pending_2fa_token: str = Form(...),
    code: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Проверка кода 2FA и установка сессии."""
    from app.api.routes.auth import create_access_token
    from datetime import timedelta
    from sqlalchemy import select
    from app.models.user import User
    from app.core.redis import redis_client
    from app.services.settings_service import SettingsService
    import json
    import structlog

    logger = structlog.get_logger()
    code = (code or "").strip().replace(" ", "")
    if len(code) != 6 or not code.isdigit():
        return templates.TemplateResponse(
            "admin/login.html",
            {
                "request": request,
                "error": "Введите 6 цифр кода",
                "step_2fa": True,
                "pending_2fa_token": pending_2fa_token,
            },
        )

    redis_key = f"2fa:pending:{pending_2fa_token}"
    try:
        raw = await redis_client.get(redis_key)
    except Exception as e:
        logger.warning("2fa_redis_get_error", error=str(e))
        return templates.TemplateResponse(
            "admin/login.html",
            {"request": request, "error": "Ошибка проверки кода. Попробуйте войти снова."},
        )

    if not raw:
        return templates.TemplateResponse(
            "admin/login.html",
            {"request": request, "error": "Код истёк или неверен. Выполните вход заново."},
        )

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        await redis_client.delete(redis_key)
        return templates.TemplateResponse(
            "admin/login.html",
            {"request": request, "error": "Ошибка данных. Выполните вход заново."},
        )

    if data.get("code") != code:
        return templates.TemplateResponse(
            "admin/login.html",
            {
                "request": request,
                "error": "Неверный код",
                "step_2fa": True,
                "pending_2fa_token": pending_2fa_token,
            },
        )

    user_id = data.get("user_id")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        await redis_client.delete(redis_key)
        return templates.TemplateResponse(
            "admin/login.html",
            {"request": request, "error": "Пользователь не найден или заблокирован."},
        )

    await redis_client.delete(redis_key)

    try:
        _svc = SettingsService(db)
        _all = await _svc.get_all_settings()
        timeout_minutes = _all.security.session_timeout or getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60)
    except Exception:
        timeout_minutes = getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60)

    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=timedelta(minutes=timeout_minutes),
    )
    logger.info("User login successful (2FA)", user_id=user.id, email=user.email)

    response = RedirectResponse(url="/admin", status_code=303)
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=timeout_minutes * 60,
        path="/",
        secure=settings.is_production,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/", response_class=RedirectResponse)
async def root(current_user=Depends(get_current_user_optional)):
    if current_user:
        return RedirectResponse("/admin")
    return RedirectResponse("/admin/login")