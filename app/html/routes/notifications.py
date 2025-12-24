from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.html.deps import CurrentActiveUser
from app.html.mock import NOTIFICATIONS_MOCK_DATA
from app.html.filters import datetime_format

router = APIRouter()

templates = Jinja2Templates(directory="templates")
# Add datetime filter to templates
templates.env.filters["datetime_format"] = datetime_format

@router.get("/notifications", response_class=HTMLResponse)
async def notifications_page(
    request: Request,
    current_user=CurrentActiveUser
):
    """Notifications page."""
    notifications = NOTIFICATIONS_MOCK_DATA
    
    context = {
        "request": request,
        "notifications": notifications,
        "total_count": len(notifications),
        "current_user": current_user
    }
    return templates.TemplateResponse("notifications.html", context)