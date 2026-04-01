"""Shared Jinja2 template configuration for HTML routes."""

from fastapi.templating import Jinja2Templates

from app.html.filters import datetime_format, storage_url, tojson_filter
from app.html.i18n import SUPPORTED_LANGUAGES, t


def build_templates() -> Jinja2Templates:
    """Create a configured Jinja2Templates instance with shared filters."""
    templates = Jinja2Templates(directory="templates")
    templates.env.filters["datetime_format"] = datetime_format
    templates.env.filters["storage_url"] = storage_url
    templates.env.filters["tojson"] = tojson_filter
    templates.env.globals["t"] = t
    templates.env.globals["supported_languages"] = SUPPORTED_LANGUAGES
    return templates


templates = build_templates()
