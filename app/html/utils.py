"""Small shared helpers for HTML route handlers."""

from fastapi.responses import RedirectResponse


def login_redirect() -> RedirectResponse:
    """Redirect unauthenticated users to the admin login page."""
    return RedirectResponse(url="/admin/login", status_code=303)


def require_active_user(current_user):
    """Return a login redirect when user is missing or inactive."""
    if not current_user or not getattr(current_user, "is_active", False):
        return login_redirect()
    return None


def serialize_datetime(value):
    """Convert datetime-like values to ISO strings for template contexts."""
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def serialize_fields(data: dict, *field_names: str) -> dict:
    """Serialize selected mapping fields in-place and return the mapping."""
    for field_name in field_names:
        if field_name in data:
            data[field_name] = serialize_datetime(data[field_name])
    return data
