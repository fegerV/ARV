from datetime import datetime
from jinja2 import pass_environment
from markupsafe import Markup

@pass_environment
def datetime_format(env, value, fmt="%d.%m.%Y %H:%M"):
    if not value:
        return Markup("—")
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    if isinstance(value, datetime):
        return env.filters["escape"](value.strftime(fmt))
    return Markup("—")