"""Shared Jinja2 template configuration for HTML routes."""

from fastapi.templating import Jinja2Templates

from app.html.filters import datetime_format, storage_url, tojson_filter


def build_templates() -> Jinja2Templates:
    """Create a configured Jinja2Templates instance with shared filters."""
    templates = Jinja2Templates(directory="templates")
    templates.env.filters["datetime_format"] = datetime_format
    templates.env.filters["storage_url"] = storage_url
    templates.env.filters["tojson"] = tojson_filter
    return templates


templates = build_templates()
