from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.html.deps import get_html_db
from app.api.routes.auth import get_current_user_optional
from app.html.mock import ANALYTICS_MOCK_DATA
from app.html.filters import datetime_format

router = APIRouter()

templates = Jinja2Templates(directory="templates")
# Add datetime filter to templates
templates.env.filters["datetime_format"] = datetime_format

@router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(
    request: Request,
    current_user=Depends(get_current_user_optional)
):
    """Analytics page."""
    if not current_user:
        # Redirect to login page if user is not authenticated
        return RedirectResponse(url="/admin/login", status_code=303)
    
    if not current_user.is_active:
        # Redirect to login page if user is not active
        return RedirectResponse(url="/admin/login", status_code=303)
    analytics_data = ANALYTICS_MOCK_DATA
    
    context = {
        "request": request,
        "analytics_data": analytics_data["analytics_data"],
        "current_user": current_user
    }
    return templates.TemplateResponse("analytics.html", context)