from datetime import datetime
from fastapi import Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from app.html.deps import get_html_db, CurrentActiveUser
from app.api.routes.analytics import analytics_summary
from app.html.mock import DASHBOARD_MOCK_DATA
from app.api.routes.auth import get_current_user_optional
from app.html.filters import datetime_format

router = APIRouter()

templates = Jinja2Templates(directory="templates")
# Add datetime filter to templates
templates.env.filters["datetime_format"] = datetime_format

@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_html_db),
    current_user=CurrentActiveUser,
):
    try:
        result = await analytics_summary(db=db)
        dashboard_data = dict(result)
    except Exception:
        dashboard_data = DASHBOARD_MOCK_DATA          # fallback

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            **dashboard_data,
        },
    )