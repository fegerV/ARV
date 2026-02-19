"""Страница просмотра логов сервера в админке."""

import asyncio
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.api.routes.auth import get_current_user_optional
from app.core.config import settings
from app.html.filters import tojson_filter

router = APIRouter()
logger = structlog.get_logger()
templates = Jinja2Templates(directory="templates")
templates.env.filters["tojson"] = tojson_filter


def _read_log_lines_from_file(path: str, max_lines: int) -> tuple[list[str], str | None]:
    """
    Читает последние max_lines строк из файла.
    Возвращает (список строк, None) при успехе или ([], сообщение об ошибке).
    """
    try:
        p = Path(path)
        if not p.exists():
            return [], f"Файл не найден: {path}"
        if not p.is_file():
            return [], f"Не файл: {path}"
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        # последние max_lines
        lines = lines[-max_lines:] if len(lines) > max_lines else lines
        return [line.rstrip("\n\r") for line in lines], None
    except OSError as e:
        return [], str(e)


async def _read_log_lines_from_journalctl(unit: str, max_lines: int) -> tuple[list[str], str | None]:
    """
    Запускает journalctl -u <unit> -n <max_lines> --no-pager.
    Возвращает (список строк, None) при успехе или ([], сообщение об ошибке).
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "journalctl",
            "-u",
            unit,
            "-n",
            str(max_lines),
            "--no-pager",
            "-o",
            "short-iso",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15.0)
        if proc.returncode != 0:
            err = (stderr or b"").decode("utf-8", errors="replace").strip()
            return [], err or f"journalctl вернул код {proc.returncode}"
        text = (stdout or b"").decode("utf-8", errors="replace")
        lines = [line.rstrip("\n\r") for line in text.splitlines()]
        return lines, None
    except asyncio.TimeoutError:
        return [], "Таймаут выполнения journalctl"
    except FileNotFoundError:
        return [], "journalctl не найден (не Linux/systemd?)"
    except OSError as e:
        return [], str(e)


async def _get_log_lines(lines_param: int | None) -> tuple[list[str], str, str]:
    """
    Определяет источник логов (файл или journalctl), читает данные.
    Возвращает (список строк, источник для отображения, сообщение об ошибке или пусто).
    """
    max_lines = min(lines_param or settings.LOG_MAX_LINES, 2000)
    max_lines = max(1, max_lines)

    if settings.LOG_FILE and Path(settings.LOG_FILE).exists():
        lines, err = _read_log_lines_from_file(settings.LOG_FILE, max_lines)
        if err:
            return [], "file", err
        return lines, "file", ""

    lines, err = await _read_log_lines_from_journalctl(
        settings.LOG_JOURNALCTL_UNIT, max_lines
    )
    if err:
        return [], "journalctl", err
    return lines, "journalctl", ""


async def get_log_content(lines_param: int | None = None) -> tuple[list[str], str, str]:
    """Читает логи и возвращает (строки, источник, ошибка)."""
    return await _get_log_lines(lines_param)


@router.get("/admin/logs", response_class=HTMLResponse)
async def admin_logs_page(
    request: Request,
    current_user=Depends(get_current_user_optional),
):
    """Страница просмотра логов (только для авторизованных)."""
    if not current_user or not current_user.is_active:
        return RedirectResponse(url="/admin/login", status_code=303)

    lines, source, error = await get_log_content(None)
    context = {
        "request": request,
        "current_user": current_user,
        "log_lines": lines,
        "log_source": source,
        "log_error": error,
        "max_lines": settings.LOG_MAX_LINES,
    }
    return templates.TemplateResponse("admin/logs.html", context)


@router.get("/api/admin/logs")
async def api_admin_logs(
    lines: int | None = None,
    current_user=Depends(get_current_user_optional),
):
    """API для получения логов (JSON), для обновления без перезагрузки страницы."""
    if not current_user or not current_user.is_active:
        return JSONResponse(
            status_code=401,
            content={"detail": "Unauthorized"},
        )
    log_lines, source, error = await get_log_content(lines)
    return {
        "lines": log_lines,
        "source": source,
        "error": error or None,
        "count": len(log_lines),
    }
