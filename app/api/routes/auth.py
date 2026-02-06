from fastapi import APIRouter, HTTPException, Depends, status, Request, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.middleware.rate_limiter import rate_limit
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from app.core.security import verify_password, create_access_token, get_password_hash, decode_token
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

async def get_current_user(
    request: Request,
    token: str = None,
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from either token or cookie"""
    # First try to get token from header if not provided
    if not token:
        token = request.headers.get("Authorization")
        if token and token.startswith("Bearer "):
            token = token[7:]
        elif not token:
            # If no header token, try to get from cookie
            token = request.cookies.get("access_token")
    
    # If we have a token, try to validate it
    if token:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        payload = decode_token(token)
        if payload is not None:
            email: str = payload.get("sub")
            if email:
                result = await db.execute(select(User).where(User.email == email))
                user = result.scalar_one_or_none()
                if user:
                    return user
    
    # If no token or token is invalid, raise exception
    raise credentials_exception

async def get_current_user_from_cookie(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from cookie"""
    access_token = request.cookies.get("access_token")
    if not access_token:
        return None

    payload = decode_token(access_token)
    if payload is None:
        return None
    
    email: str = payload.get("sub")
    if email is None:
        return None
    
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if user is None:
        return None
    
    return user

async def get_current_user_optional(
    request: Request,
    token: str = None,
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user from either token or cookie, returns None if not authenticated"""
    # First try to get token from header if not provided
    if not token:
        token = request.headers.get("Authorization")
        if token and token.startswith("Bearer "):
            token = token[7:]
        elif not token:
            # If no header token, try to get from cookie
            token = request.cookies.get("access_token")
    
    # If we have a token, try to validate it
    if token:
        payload = decode_token(token)
        if payload is not None:
            email: str = payload.get("sub")
            if email:
                result = await db.execute(select(User).where(User.email == email))
                user = result.scalar_one_or_none()
                if user:
                    return user

    # If no token or token is invalid, return None
    return None

async def get_current_active_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current active user from either token or cookie"""
    # First try to get from Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        payload = decode_token(token)
        if payload:
            email: str = payload.get("sub")
            if email:
                result = await db.execute(select(User).where(User.email == email))
                user = result.scalar_one_or_none()
                if user and user.is_active:
                    return user
    
    # If no token or token invalid, try to get from cookie
    token = request.cookies.get("access_token")
    if token:
        payload = decode_token(token)
        if payload:
            email: str = payload.get("sub")
            if email:
                result = await db.execute(select(User).where(User.email == email))
                user = result.scalar_one_or_none()
                if user and user.is_active:
                    return user
    
    raise HTTPException(status_code=401, detail="Inactive user or not authenticated")

def create_access_token_cookie(response: Response, access_token: str):
    """Set access token in cookie for HTML interface"""
    settings = get_settings()
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

@router.post("/login", response_model=Token)
@rate_limit(max_requests=10, window_size="minute", per_user=False)  # 10 login attempts per minute per IP
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
    settings = get_settings()
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

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user)):
    """Logout user (JWT is stateless, just log the event)"""
    logger.info("User logout", user_id=current_user.id, email=current_user.email)
    return {"message": "Успешно вышли из системы"}

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
