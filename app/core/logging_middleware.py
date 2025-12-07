# app/core/logging_middleware.py
"""
Enhanced logging middleware with request ID, user ID, and company ID tracking.
"""
import uuid
import structlog
from datetime import datetime
from fastapi import Request
from prometheus_client import Summary, Counter

# Prometheus metrics
REQUEST_DURATION = Summary('api_request_duration_seconds', 'API request duration seconds', ['method', 'path'])
REQUEST_COUNT = Counter('api_request_count_total', 'Total number of API requests', ['method', 'path', 'status'])

# Structured logger
logger = structlog.get_logger()


async def logging_middleware(request: Request, call_next):
    """
    Enhanced logging middleware with structured logging and request tracking.
    
    Adds the following to all log entries:
    - request_id: Unique identifier for the request
    - user_id: Authenticated user ID (if available)
    - company_id: Company ID associated with the user (if available)
    - method: HTTP method
    - path: Request path
    - client_host: Client IP address
    """
    # Generate unique request ID
    request_id = str(uuid.uuid4())
    
    # Extract user information from token if available
    user_id = None
    company_id = None
    
    try:
        # Try to extract user info from authorization header
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            from app.core.security import decode_token
            token = auth_header.split(" ")[1]
            payload = decode_token(token)
            if payload:
                user_id = payload.get("user_id")
                
                # If we have user_id, try to get company_id
                if user_id:
                    # We would typically get company_id from the database here
                    # For now, we'll leave it as None and let endpoints populate it
                    pass
    except Exception:
        # Silently ignore token decoding errors
        pass
    
    # Add context variables for structured logging
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        user_id=user_id,
        company_id=company_id,
    )
    
    start_time = datetime.utcnow()
    
    # Log request start
    logger.info(
        "http_request_started",
        method=request.method,
        path=request.url.path,
        client_host=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    
    try:
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = (datetime.utcnow() - start_time).total_seconds()
        REQUEST_DURATION.labels(request.method, request.url.path).observe(duration)
        REQUEST_COUNT.labels(request.method, request.url.path, response.status_code).inc()
        
        # Log response
        logger.info(
            "http_request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_seconds=duration,
        )
        
        return response
        
    except Exception as e:
        # Calculate duration for failed requests
        duration = (datetime.utcnow() - start_time).total_seconds()
        REQUEST_DURATION.labels(request.method, request.url.path).observe(duration)
        REQUEST_COUNT.labels(request.method, request.url.path, 500).inc()
        
        # Log error
        logger.exception(
            "http_request_failed",
            method=request.method,
            path=request.url.path,
            duration_seconds=duration,
        )
        
        # Re-raise the exception
        raise