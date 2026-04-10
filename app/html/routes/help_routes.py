"""HTML route for the Help / Documentation page."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from pathlib import Path

from app.api.routes.auth import get_current_user_optional
from app.html.templating import templates
from app.html.utils import require_active_user

router = APIRouter()


@router.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    """Return robots.txt file content."""
    robots_path = Path("robots.txt")
    if robots_path.exists():
        content = robots_path.read_text(encoding="utf-8")
    else:
        # Default content if file doesn't exist
        content = "User-agent: *\nDisallow: /admin\n"
    return PlainTextResponse(content=content, media_type="text/plain")


@router.get("/help", response_class=HTMLResponse)
async def help_page(
    request: Request,
    current_user=Depends(get_current_user_optional),
):
    """Справка и документация по работе с платформой."""
    redirect = require_active_user(current_user)
    if redirect:
        return redirect

    return templates.TemplateResponse(
        "help.html",
        {"request": request, "current_user": current_user},
    )
