from fastapi import APIRouter, HTTPException, Depends, status, Request, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from app.middleware.rate_limiter import rate_limit
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from app.core.security import (
    verify_password,
    create_access_token,
    get_password_hash,
    decode_token,
    needs_password_rehash,
)
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import Token, UserResponse, RegisterRequest, RegisterResponse
from app.core.config import get_settings
import structlog

router = APIRouter(tags=["auth"])

# Export the functions that will be imported in main.py
__all__ = [
    "get_current_user",
    "get_current_active_user",
    "get_current_user_optional"
]
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
logger = structlog.get_logger()

# Rate limiting constants
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)


def _extract_request_token(request: Request, token: str = None) -> str | None:
    """Read bearer token from explicit arg, Authorization header, or cookie."""
    if token:
        return token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]
    return request.cookies.get("access_token")


async def _get_user_from_token(db: AsyncSession, token: str | None) -> User | None:
    """Resolve a user from a decoded JWT token."""
    if not token:
        return None
    payload = decode_token(token)
    if payload is None:
        return None
    email: str | None = payload.get("sub")
    if not email:
        return None
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()

async def get_current_user(
    request: Request,
    token: str = None,
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from either token or cookie"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user = await _get_user_from_token(db, _extract_request_token(request, token))
    if user:
        return user
    raise credentials_exception

async def get_current_user_from_cookie(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from cookie"""
    return await _get_user_from_token(db, request.cookies.get("access_token"))

async def get_current_user_optional(
    request: Request,
    token: str = None,
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user from either token or cookie, returns None if not authenticated"""
    return await _get_user_from_token(db, _extract_request_token(request, token))

async def get_current_active_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current active user from either token or cookie"""
    user = await _get_user_from_token(db, _extract_request_token(request))
    if user and user.is_active:
        return user
    raise HTTPException(status_code=401, detail="Inactive user or not authenticated")

async def get_session_timeout_minutes(db: AsyncSession) -> int:
    """Read session timeout from settings with a safe fallback."""
    settings = get_settings()
    try:
        from app.services.settings_service import SettingsService

        service = SettingsService(db)
        timeout = await service.get_int_setting("session_timeout", settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return max(timeout, 1)
    except Exception:
        return settings.ACCESS_TOKEN_EXPIRE_MINUTES


def create_access_token_cookie(response: Response, access_token: str, timeout_minutes: int) -> None:
    """Set access token in cookie for HTML interface."""
    settings = get_settings()
    lifetime_seconds = max(int(timeout_minutes) * 60, 60)
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=lifetime_seconds,
        expires=lifetime_seconds,
        path="/",
        secure=settings.is_production,  # Use secure cookies in production
        httponly=True,
        samesite="lax",
    )


def clear_access_token_cookie(response: Response) -> None:
    response.delete_cookie("access_token", path="/", samesite="lax")


def clear_auth_cookies(response: Response) -> None:
    """Clear browser authentication cookies."""
    clear_access_token_cookie(response)
    response.delete_cookie("csrf_token", path="/", samesite="lax")

@router.post("/login", response_model=Token)
@rate_limit("10/minute")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Authenticate admin user with rate limiting - API version"""
    # Get user by email
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    
    # Check if account is locked
    if user and user.locked_until:
        if datetime.utcnow() < user.locked_until:
            logger.warning("Login attempt on locked account", email=form_data.username)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "detail": "Аккаунт временно заблокирован",
                    "locked_until": user.locked_until.isoformat(),
                }
            )
        else:
            # Unlock account
            user.locked_until = None
            user.login_attempts = 0
            await db.commit()

    # Verify credentials
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning("Failed login attempt", email=form_data.username)
        
        if user:
            # Increment login attempts
            user.login_attempts += 1
            
            # Lock account after MAX_LOGIN_ATTEMPTS
            if user.login_attempts >= MAX_LOGIN_ATTEMPTS:
                user.locked_until = datetime.utcnow() + LOCKOUT_DURATION
                await db.commit()
                
                logger.warning("Account locked due to excessive login attempts",
                             email=form_data.username,
                             attempts=user.login_attempts)
                
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "detail": f"Слишком много неудачных попыток. Аккаунт заблокирован на {LOCKOUT_DURATION.seconds // 60} минут",
                        "locked_until": user.locked_until.isoformat(),
                    }
                )
            
            await db.commit()
            attempts_left = MAX_LOGIN_ATTEMPTS - user.login_attempts
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "detail": "Неверный email или пароль",
                    "attempts_left": attempts_left,
                },
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Don't reveal if user exists
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт заблокирован"
        )
    
    if needs_password_rehash(user.hashed_password):
        user.hashed_password = get_password_hash(form_data.password)

    # Reset login attempts on successful login
    user.login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.utcnow()
    await db.commit()
    
    timeout_minutes = await get_session_timeout_minutes(db)
    access_token_expires = timedelta(minutes=timeout_minutes)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    logger.info("User login successful", user_id=user.id, email=user.email)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.from_orm(user)
    }

@router.post("/login-form", response_class=HTMLResponse)
async def login_form(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Handle form-based login for HTML interface"""
    # Create templates instance to render login page with errors
    templates = Jinja2Templates(directory="templates")
    
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
            return templates.TemplateResponse("auth/login.html", context)
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
            if user.login_attempts >= MAX_LOGIN_ATTEMPTS:
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
                return templates.TemplateResponse("auth/login.html", context)
            
            await db.commit()
            attempts_left = MAX_LOGIN_ATTEMPTS - user.login_attempts
            
            context = {
                "request": request,
                "error": "Неверный email или пароль",
                "attempts_left": attempts_left
            }
            return templates.TemplateResponse("auth/login.html", context)
        
        # Don't reveal if user exists
        context = {
            "request": request,
            "error": "Неверный email или пароль"
        }
        return templates.TemplateResponse("auth/login.html", context)
    
    if not user.is_active:
        context = {
            "request": request,
            "error": "Аккаунт заблокирован"
        }
        return templates.TemplateResponse("auth/login.html", context)
    
    if needs_password_rehash(user.hashed_password):
        user.hashed_password = get_password_hash(password)

    # Reset login attempts on successful login
    user.login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.utcnow()
    await db.commit()
    
    _timeout = await get_session_timeout_minutes(db)
    access_token_expires = timedelta(minutes=_timeout)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    logger.info("User login successful", user_id=user.id, email=user.email)
    
    # Create response and set cookie
    response = RedirectResponse(url="/admin", status_code=303)
    create_access_token_cookie(response, access_token, _timeout)
    return response

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user)):
    """Logout user and clear cookie-based session state."""
    logger.info("User logout", user_id=current_user.id, email=current_user.email)
    response = JSONResponse({"message": "Успешно вышли из системы"})
    clear_auth_cookies(response)
    return response

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user info"""
    return UserResponse.from_orm(current_user)

@router.post("/register", response_model=RegisterResponse)
async def register_user(
    request: Request,
    user_data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Register a new user (admin only)"""
    # Check if current user is admin
    if current_user.role != "admin":
        logger.warning(
            "unauthorized_registration_attempt", 
            user_id=current_user.id, 
            email=current_user.email,
            requested_role=user_data.role
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create new users"
        )
    
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        logger.warning(
            "duplicate_email_registration_attempt",
            email=user_data.email,
            attempted_by=current_user.email
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        role=user_data.role,
        is_active=True
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    logger.info(
        "user_registered",
        user_id=new_user.id,
        email=new_user.email,
        role=new_user.role,
        created_by=current_user.email
    )
    
    return RegisterResponse(
        user=UserResponse.from_orm(new_user),
        message="User created successfully"
    )
