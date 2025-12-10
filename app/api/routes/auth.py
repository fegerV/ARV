from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from app.core.security import verify_password, create_access_token, get_password_hash
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import Token, UserResponse, RegisterRequest, RegisterResponse
import structlog

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
logger = structlog.get_logger()

# Rate limiting constants
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(minutes=15)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    from app.core.security import decode_token
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    
    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception
    
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Authenticate admin user with rate limiting"""
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
    from app.core.config import get_settings
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
            requested_role=user_data.role.value
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
        role=new_user.role.value,
        created_by=current_user.email
    )
    
    return RegisterResponse(
        user=UserResponse.from_orm(new_user),
        message="User created successfully"
    )
