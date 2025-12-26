from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.routes.auth import get_current_user_optional
from app.middleware.rate_limiter import limiter
from app.html.filters import datetime_format
from app.core.database import get_db

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


@router.post("/admin/login-form", response_class=HTMLResponse)
async def login_form(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Handle form-based login for HTML interface"""
    from app.api.routes.auth import verify_password, create_access_token
    from datetime import datetime, timedelta
    from sqlalchemy import select
    from app.models.user import User
    from app.core.config import get_settings
    import structlog
    
    logger = structlog.get_logger()
    
    # Get user by email
    result = await db.execute(select(User).where(User.email == username))
    user = result.scalar_one_or_none()
    
    # Check if account is locked
    if user and user.locked_until:
        if datetime.utcnow() < user.locked_until:
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
            # Increment login attempts
            user.login_attempts += 1
            
            # Lock account after MAX_LOGIN_ATTEMPTS
            if user.login_attempts >= 5:
                from datetime import timedelta
                LOCKOUT_DURATION = timedelta(minutes=15)
                user.locked_until = datetime.utcnow() + LOCKOUT_DURATION
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
    
    # Reset login attempts on successful login
    user.login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.utcnow()
    await db.commit()
    
    # Create JWT token with configured expiry
    settings = get_settings()
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    logger.info("User login successful", user_id=user.id, email=user.email)
    
    # Create response and set cookie
    response = RedirectResponse(url="/admin", status_code=303)
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=3600,
        expires=3600,
        path="/",
        secure=settings.is_production,  # Use secure cookies in production
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/", response_class=RedirectResponse)
async def root(current_user=Depends(get_current_user_optional)):
    if current_user:
        return RedirectResponse("/admin")
    return RedirectResponse("/admin/login")