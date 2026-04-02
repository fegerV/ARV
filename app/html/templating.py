"""Shared Jinja2 template configuration for HTML routes."""

from fastapi.templating import Jinja2Templates

from app.html.filters import datetime_format, storage_url, tojson_filter
from app.html.i18n import SUPPORTED_LANGUAGES, get_request_locale, t


class AdminTemplates(Jinja2Templates):
    """Jinja2Templates variant that keeps request.state.locale in sync with session."""

    def TemplateResponse(self, name, context, *args, **kwargs):  # noqa: N802
        request = context.get("request") if isinstance(context, dict) else None
        if request is not None:
            get_request_locale(request)
        return super().TemplateResponse(name, context, *args, **kwargs)


def build_templates() -> Jinja2Templates:
    """Create a configured Jinja2Templates instance with shared filters."""
    templates = AdminTemplates(directory="templates")
    templates.env.filters["datetime_format"] = datetime_format
    templates.env.filters["storage_url"] = storage_url
    templates.env.filters["tojson"] = tojson_filter
    templates.env.globals["t"] = t
    templates.env.globals["supported_languages"] = SUPPORTED_LANGUAGES
    return templates


templates = build_templates()
