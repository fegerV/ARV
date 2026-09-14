"""Small shared helpers for HTML route handlers."""

from fastapi.responses import HTMLResponse, RedirectResponse


def login_redirect() -> RedirectResponse:
    """Redirect unauthenticated users to the admin login page."""
    return RedirectResponse(url="/admin/login", status_code=303)


def forbidden_response(message: str = "Access denied") -> HTMLResponse:
    """Return a 403 page for authenticated-but-unauthorised requests."""
    return HTMLResponse(message, status_code=403)


def require_active_user(current_user):
    """Return a login redirect when user is missing or inactive."""
    if not current_user or not getattr(current_user, "is_active", False):
        return login_redirect()
    return None


def is_super_admin(current_user) -> bool:
    """Return True only when the user is explicitly flagged as a super admin."""
    return bool(getattr(current_user, "is_super_admin", False))


def user_can_access_company(current_user, company_id) -> bool:
    """Return True when the user may access resources of *company_id* (fail-closed)."""
    if current_user is None:
        return False
    if is_super_admin(current_user):
        return True
    user_company_id = getattr(current_user, "company_id", None)
    if user_company_id is None or company_id is None:
        return False
    return user_company_id == company_id


def require_super_admin(current_user):
    """Return a response when the user is not an active super admin, else None.

    Use for global/privileged admin pages (settings, logs, backups, user
    management). Returns a login redirect for unauthenticated users and a 403
    for authenticated non-super-admins.
    """
    redirect = require_active_user(current_user)
    if redirect:
        return redirect
    if not is_super_admin(current_user):
        return forbidden_response("Super admin access required")
    return None


def require_company_scope(current_user, company_id):
    """Return a response when the user cannot access *company_id*, else None."""
    redirect = require_active_user(current_user)
    if redirect:
        return redirect
    if not user_can_access_company(current_user, company_id):
        return forbidden_response("Access denied to this company")
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


def serialize_nested(value):
    """Recursively convert datetime-like values in nested lists/dicts."""
    if isinstance(value, dict):
        return {key: serialize_nested(item) for key, item in value.items()}
    if isinstance(value, list):
        return [serialize_nested(item) for item in value]
    return serialize_datetime(value)
