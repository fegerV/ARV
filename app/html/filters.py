from datetime import datetime
from jinja2 import pass_environment
from markupsafe import Markup
import json

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


def tojson_filter(value):
    """Custom JSON filter that handles datetime objects and other Python types."""
    def json_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, '__dict__'):
            return obj.__dict__
        raise TypeError(f"Type {type(obj)} not serializable")
    
    try:
        return json.dumps(value, default=json_serializer, ensure_ascii=False)
    except Exception as e:
        # Fallback to simple string representation
        return json.dumps(str(value), ensure_ascii=False)