from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.html.deps import CurrentActiveUser
from app.html.mock import ANALYTICS_MOCK_DATA
from app.html.filters import datetime_format

router = APIRouter()

templates = Jinja2Templates(directory="templates")
# Add datetime filter to templates
templates.env.filters["datetime_format"] = datetime_format

@router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(
    request: Request,
    current_user=CurrentActiveUser
):
    """Analytics page."""
    analytics_data = ANALYTICS_MOCK_DATA
    
    context = {
        "request": request,
        "analytics_data": analytics_data["analytics_data"],
        "current_user": current_user
    }
    return templates.TemplateResponse("analytics.html", context)