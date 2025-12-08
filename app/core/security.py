from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
from app.core.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password hash"""
    # Bcrypt has a 72-byte limit, truncate if necessary
    if len(plain_password.encode('utf-8')) > 72:
        plain_password = plain_password[:72]
    
    # Check if it's a SHA256 fallback hash (uses _ separator)
    if hashed_password.startswith('sha256_'):
        import hashlib
        return hashed_password == f"sha256_{hashlib.sha256(plain_password.encode()).hexdigest()}"
    
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # Catch all exceptions (ValueError, TypeError, AttributeError, etc)
        # that might occur during bcrypt initialization or verification
        return False

def get_password_hash(password: str) -> str:
    """Hash password"""
    # Bcrypt has a 72-byte limit, truncate if necessary
    if len(password.encode('utf-8')) > 72:
        password = password[:72]
    try:
        return pwd_context.hash(password)
    except Exception:
        # Fallback if bcrypt fails - use SHA256 with _ separator ($ is problematic in some shells)
        import hashlib
        return f"sha256_{hashlib.sha256(password.encode()).hexdigest()}"

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def decode_token(token: str) -> Optional[dict]:
    """Decode JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        return None
