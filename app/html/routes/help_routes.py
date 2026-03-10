"""HTML route for the Help / Documentation page."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.api.routes.auth import get_current_user_optional

router = APIRouter()
templates = Jinja2Templates(directory="templates")


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
    if not current_user:
        return RedirectResponse(url="/admin/login", status_code=303)
    if not current_user.is_active:
        return RedirectResponse(url="/admin/login", status_code=303)

    return templates.TemplateResponse(
        "help.html",
        {"request": request, "current_user": current_user},
    )
