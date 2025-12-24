from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.html.deps import CurrentActiveUser
from app.html.mock import STORAGE_MOCK_DATA
from app.html.filters import datetime_format

router = APIRouter()

templates = Jinja2Templates(directory="templates")
# Add datetime filter to templates
templates.env.filters["datetime_format"] = datetime_format

@router.get("/storage", response_class=HTMLResponse)
async def storage_page(
    request: Request,
    current_user=CurrentActiveUser
):
    """Storage page."""
    storage_info = STORAGE_MOCK_DATA
    
    context = {
        "request": request,
        "storage_info": storage_info["storage_info"],
        "current_user": current_user
    }
    return templates.TemplateResponse("storage.html", context)