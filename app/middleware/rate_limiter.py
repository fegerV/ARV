from fastapi import HTTPException, status, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import time
from typing import Dict, Any

# Initialize rate limiter with IP address as default key
limiter = Limiter(key_func=get_remote_address)

def get_user_rate_limit_key(request: Request) -> str:
    """Generate a rate limit key based on the request - IP for unauthenticated, user ID for authenticated"""
    # Check if the request has an authenticated user
    try:
        # Extract user from request state if available
        current_user = getattr(request.state, "user", None)
        if current_user and hasattr(current_user, "id"):
            # For authenticated users, use user ID as part of the key
            return f"user_{current_user.id}"
        else:
            # For unauthenticated requests, use IP address
            return get_remote_address(request)
    except:
        # Fallback to IP address if user extraction fails
        return get_remote_address(request)

def add_rate_limit_headers(response, request_limit, current_limit, window_size=60):
    """Add rate limit headers to response"""
    response.headers["X-RateLimit-Limit"] = str(request_limit)
    response.headers["X-RateLimit-Remaining"] = str(max(0, current_limit))
    response.headers["X-RateLimit-Reset"] = str(int(time.time()) + window_size)

def setup_rate_limiting(app):
    """Setup rate limiting for the FastAPI application"""
    # Set up the limiter instance
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # Add rate limit middleware to update response headers with rate limit info
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        response = await call_next(request)
        
        # Add rate limit headers to response
        # Note: slowapi automatically handles rate limiting,
        # we're just adding the headers for client information
        current_user = getattr(request.state, "user", None)
        if current_user and hasattr(current_user, "id"):
            # Authenticated user - 100 requests per hour
            add_rate_limit_headers(response, 100, 100, 3600)  # 1 hour window
        else:
            # Unauthenticated user - 100 requests per minute
            add_rate_limit_headers(response, 100, 100, 60)  # 1 minute window
        
        return response

# Decorator for applying rate limits to specific routes
def rate_limit(max_requests: int, window_size: str, per_user: bool = True):
    """
    Decorator to apply rate limiting to specific routes
    :param max_requests: Maximum number of requests allowed
    :param window_size: Time window (e.g., "minute", "hour", "day")
    :param per_user: Whether to apply rate limit per user or per IP
    """
    def decorator(func):
        # Create a wrapper function that adds rate limiting
        if per_user:
            # Use user-specific rate limiting
            limited_func = limiter.limit(f"{max_requests}/{window_size}", key_func=get_user_rate_limit_key)(func)
        else:
            # Use IP-based rate limiting
            limited_func = limiter.limit(f"{max_requests}/{window_size}")(func)
        return limited_func
    return decorator