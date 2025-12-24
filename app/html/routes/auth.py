from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.api.routes.auth import get_current_user_optional
from app.middleware.rate_limiter import limiter
from app.html.filters import datetime_format

router = APIRouter()

templates = Jinja2Templates(directory="templates")
# Add datetime filter to templates
templates.env.filters["datetime_format"] = datetime_format

@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Admin login page."""
    # Apply rate limiting
    limiter.limit("5/minute")  # Rate limit to 5 requests per minute per IP
    
    context = {
        "request": request,
        "error": None,
        "locked_until": None,
        "attempts_left": None
    }
    return templates.TemplateResponse("auth/login.html", context)


@router.get("/", response_class=RedirectResponse)
async def root(current_user=Depends(get_current_user_optional)):
    if current_user:
        return RedirectResponse("/admin")
    return RedirectResponse("/admin/login")