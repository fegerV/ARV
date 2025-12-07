# Unified Error Response Format

## Overview

All API errors in the Vertex AR platform follow a standardized JSON format for consistent client-side handling.

## Error Response Structure

```json
{
  "detail": "Human-readable error message",
  "code": "MACHINE_READABLE_ERROR_CODE",
  "meta": {
    "field": "email",
    "hint": "Additional data for UI"
  }
}
```

## Fields

### detail (string)
A human-readable message that can be displayed directly to the user (via toast/snackbar).

### code (string | null)
Machine-readable error code for conditional logic on the frontend:

Common codes:
- `AR_CONTENT_NOT_FOUND`
- `VALIDATION_ERROR`
- `STORAGE_QUOTA_EXCEEDED`
- `UNAUTHORIZED`
- `INTERNAL_ERROR`
- `NOT_FOUND`
- `FORBIDDEN`
- `CONFLICT`

### meta (object | null)
Additional data for UI handling:

#### Field Errors
For form validation errors:
```json
"meta": {
  "fields": {
    "slug": "This slug is already in use",
    "email": "Invalid email format"
  }
}
```

#### Technical Details
Technical information (not shown to users, but logged):
```json
"meta": {
  "request_id": "b2f7...",
  "debug": false
}
```

## Frontend Handling

This format is easily parsed in axios interceptors:
- `detail` goes directly to toast
- `code` and `meta.fields` enable fine-grained form field highlighting
- Special handling can be implemented based on `code`

## Examples

### Validation Error
```json
{
  "detail": "Ошибка валидации данных",
  "code": "VALIDATION_ERROR",
  "meta": {
    "fields": {
      "email": "Некорректный email",
      "password": "Пароль должен содержать минимум 8 символов"
    }
  }
}
```

### Resource Not Found
```json
{
  "detail": "AR-контент не найден",
  "code": "AR_CONTENT_NOT_FOUND",
  "meta": null
}
```

### Internal Server Error
```json
{
  "detail": "Внутренняя ошибка сервера",
  "code": "INTERNAL_ERROR",
  "meta": {
    "request_id": "abc123"
  }
}
```