from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.html.deps import CurrentActiveUser
from app.html.mock import SETTINGS_MOCK_DATA
from app.html.filters import datetime_format

router = APIRouter()

templates = Jinja2Templates(directory="templates")
# Add datetime filter to templates
templates.env.filters["datetime_format"] = datetime_format

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    current_user=CurrentActiveUser
):
    """Settings page."""
    settings = SETTINGS_MOCK_DATA
    
    context = {
        "request": request,
        "settings": settings["settings"],
        "current_user": current_user
    }
    return templates.TemplateResponse("settings.html", context)