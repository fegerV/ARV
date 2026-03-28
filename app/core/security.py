import hashlib
import re
import secrets
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from passlib.exc import UnknownHashError

from app.core.config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
_LEGACY_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


def _legacy_sha256(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def is_legacy_password_hash(hashed_password: str) -> bool:
    """Return True for old unsalted SHA-256 hashes kept for migration."""
    return bool(hashed_password and _LEGACY_SHA256_RE.fullmatch(hashed_password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against the current hash scheme or legacy SHA-256."""
    if not hashed_password:
        return False
    if is_legacy_password_hash(hashed_password):
        return secrets.compare_digest(_legacy_sha256(plain_password), hashed_password)
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except (ValueError, UnknownHashError):
        return False


def get_password_hash(password: str) -> str:
    """Hash password using the configured adaptive password scheme."""
    return pwd_context.hash(password)


def needs_password_rehash(hashed_password: str) -> bool:
    """Return True when hash should be upgraded to the current scheme."""
    if not hashed_password:
        return True
    if is_legacy_password_hash(hashed_password):
        return True
    try:
        return pwd_context.needs_update(hashed_password)
    except (ValueError, UnknownHashError):
        return True


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> Optional[dict]:
    """Decode JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
