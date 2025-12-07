# app/core/error_utils.py
"""
Utility functions for creating standardized error responses.
"""
from fastapi import HTTPException, status
from app.core.errors import APIErrorResponse


def create_error_response(status_code: int, detail: str, code: str = None, meta: dict = None) -> APIErrorResponse:
    """
    Create a standardized error response.
    
    Args:
        status_code: HTTP status code
        detail: Human-readable error message
        code: Machine-readable error code
        meta: Additional metadata
        
    Returns:
        APIErrorResponse: Standardized error response
    """
    return APIErrorResponse(
        detail=detail,
        code=code,
        meta=meta
    )


def create_validation_error(fields: dict = None, detail: str = "Ошибка валидации данных") -> APIErrorResponse:
    """
    Create a validation error response.
    
    Args:
        fields: Dictionary of field errors {field_name: error_message}
        detail: Human-readable error message
        
    Returns:
        APIErrorResponse: Validation error response
    """
    return APIErrorResponse(
        detail=detail,
        code="VALIDATION_ERROR",
        meta={"fields": fields} if fields else None
    )


def create_not_found_error(resource: str = "Resource") -> APIErrorResponse:
    """
    Create a not found error response.
    
    Args:
        resource: Name of the resource that was not found
        
    Returns:
        APIErrorResponse: Not found error response
    """
    return APIErrorResponse(
        detail=f"{resource} не найден",
        code="NOT_FOUND"
    )


def create_unauthorized_error() -> APIErrorResponse:
    """
    Create an unauthorized error response.
    
    Returns:
        APIErrorResponse: Unauthorized error response
    """
    return APIErrorResponse(
        detail="Не авторизован",
        code="UNAUTHORIZED"
    )


def create_forbidden_error() -> APIErrorResponse:
    """
    Create a forbidden error response.
    
    Returns:
        APIErrorResponse: Forbidden error response
    """
    return APIErrorResponse(
        detail="Доступ запрещен",
        code="FORBIDDEN"
    )


def create_conflict_error(detail: str = "Конфликт данных") -> APIErrorResponse:
    """
    Create a conflict error response.
    
    Args:
        detail: Human-readable error message
        
    Returns:
        APIErrorResponse: Conflict error response
    """
    return APIErrorResponse(
        detail=detail,
        code="CONFLICT"
    )