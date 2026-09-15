"""Shared Jinja2 template configuration for HTML routes."""

from fastapi.templating import Jinja2Templates

from app.html.filters import datetime_format, storage_url, tojson_filter
from app.html.i18n import SUPPORTED_LANGUAGES, get_request_locale, t


class AdminTemplates(Jinja2Templates):
    """Jinja2Templates variant that keeps request.state.locale in sync with session.

    It also normalises the legacy ``TemplateResponse(name, context)`` call style
    used throughout the HTML routes into starlette's current
    ``TemplateResponse(request, name, context)`` signature.  starlette removed the
    branch that tolerated a leading string, so without this shim every admin page
    raises ``TypeError: unhashable type: 'dict'`` on any install that satisfies
    ``requirements.txt`` (starlette >= 0.40).
    """

    def TemplateResponse(self, *args, **kwargs):  # noqa: N802
        # Legacy style: TemplateResponse("page.html", {"request": request, ...})
        if args and isinstance(args[0], str):
            name = args[0]
            context = args[1] if len(args) > 1 else kwargs.pop("context", None)
            rest = args[2:]
            context = context if isinstance(context, dict) else {}
            request = context.get("request")
            if request is None:
                raise ValueError(
                    "TemplateResponse requires a 'request' key in the context"
                )
            get_request_locale(request)
            return super().TemplateResponse(request, name, context, *rest, **kwargs)

        # Modern style: TemplateResponse(request, "page.html", {...})
        request = args[0] if args else kwargs.get("request")
        if request is not None:
            get_request_locale(request)
        return super().TemplateResponse(*args, **kwargs)


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
