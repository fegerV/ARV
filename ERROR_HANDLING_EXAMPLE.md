# Error Handling Usage Examples

## Overview

This document demonstrates how to use the standardized error handling system in the Vertex AR platform.

## Using AppException

```python
from app.core.errors import AppException

# Basic usage
raise AppException(
    status_code=404,
    detail="AR-контент не найден",
    code="AR_CONTENT_NOT_FOUND"
)

# With meta data
raise AppException(
    status_code=400,
    detail="Недостаточно прав для выполнения операции",
    code="INSUFFICIENT_PERMISSIONS",
    meta={"required_role": "admin"}
)
```

## Using Error Utilities

```python
from app.core.error_utils import (
    create_not_found_error,
    create_validation_error,
    create_unauthorized_error,
    create_conflict_error
)

# Not found error
error = create_not_found_error("AR-контент")

# Validation error with field errors
error = create_validation_error({
    "email": "Некорректный формат email",
    "password": "Пароль должен содержать минимум 8 символов"
})

# Unauthorized error
error = create_unauthorized_error()

# Conflict error
error = create_conflict_error("Компания с таким названием уже существует")
```

## In FastAPI Endpoints

```python
from fastapi import APIRouter, Depends
from app.core.errors import AppException
from app.core.error_utils import create_not_found_error

router = APIRouter()

@router.get("/ar-content/{content_id}")
async def get_ar_content(content_id: int):
    # Simulate content lookup
    content = await get_content_by_id(content_id)
    
    if not content:
        # Method 1: Direct AppException
        raise AppException(
            status_code=404,
            detail="AR-контент не найден",
            code="AR_CONTENT_NOT_FOUND"
        )
        
        # Method 2: Using error utility
        # error = create_not_found_error("AR-контент")
        # raise AppException(
        #     status_code=404,
        #     detail=error.detail,
        #     code=error.code,
        #     meta=error.meta
        # )
    
    return content
```

## Expected Response Format

All errors will be returned in the standardized format:

```json
{
  "detail": "Human-readable error message",
  "code": "MACHINE_READABLE_ERROR_CODE",
  "meta": {
    "fields": {
      "email": "Invalid email format"
    }
  }
}
```

## Frontend Integration

On the frontend, you can handle these errors in axios interceptors:

```javascript
// axios interceptor
axios.interceptors.response.use(
  response => response,
  error => {
    const { detail, code, meta } = error.response.data;
    
    // Show toast notification
    toast.error(detail);
    
    // Handle field errors
    if (meta?.fields) {
      // Highlight form fields with errors
      Object.keys(meta.fields).forEach(field => {
        // Apply error styling to form fields
      });
    }
    
    // Handle specific error codes
    switch (code) {
      case 'UNAUTHORIZED':
        // Redirect to login
        break;
      case 'FORBIDDEN':
        // Show permission denied message
        break;
    }
    
    return Promise.reject(error);
  }
);
```