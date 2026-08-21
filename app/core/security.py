import hashlib
import re
import secrets
from datetime import datetime, timedelta, UTC
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from passlib.exc import UnknownHashError

from app.core.config import get_settings
from app.core.redis import redis_client

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


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None, role: Optional[str] = None, company_id: Optional[int] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if role is not None:
        to_encode["role"] = role
    if company_id is not None:
        to_encode["company_id"] = company_id
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
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


_BLACKLIST_PREFIX = "jwt_blacklist:"


async def blacklist_token(token: str, expires_in: timedelta) -> None:
    """Add JWT token to blacklist until its natural expiry."""
    ttl_seconds = max(int(expires_in.total_seconds()), 1)
    await redis_client.setex(_BLACKLIST_PREFIX + token, ttl_seconds, "1")


async def is_token_blacklisted(token: str) -> bool:
    """Return True if the token has been revoked."""
    try:
        return await redis_client.exists(_BLACKLIST_PREFIX + token) == 1
    except Exception:
        return False


async def invalidate_user_tokens(user_id: int) -> None:
    """Invalidate all active sessions/tokens for a user.

    Uses a per-user revocation key so that future token validation can
    reject any token issued before this call.
    """
    key = f"user_revoked:{user_id}"
    try:
        await redis_client.set(key, "1")
        await redis_client.expire(key, settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    except Exception:
        pass


async def is_user_revoked(user_id: int) -> bool:
    """Return True if all tokens for the user have been invalidated."""
    try:
        return await redis_client.exists(f"user_revoked:{user_id}") == 1
    except Exception:
        return False
