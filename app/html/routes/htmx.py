"""
HTMX-ручки + Redis-кеш + лёгкий clipboard.
"""
import io
import base64
from datetime import timedelta

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import qrcode

from app.core.config import settings
from app.core.redis import redis_client
from app.html.deps import get_html_db, CurrentActiveUser
from app.api.routes.ar_content import (
    get_ar_content_by_id,
    update_ar_content,
)
from app.schemas.ar_content import ARContentUpdate

router = APIRouter(prefix="/htmx", tags=["htmx"])

QR_CACHE_TTL = 300   # 5 мин

# ---------- 1. COPY LINK (JSON + фронт делает clipboard) ----------
@router.post("/ar-content/{ar_content_id}/copy-link")
async def copy_ar_content_link(
    ar_content_id: str,
    request: Request,
    db: AsyncSession = Depends(get_html_db),
    current_user=CurrentActiveUser,
):
    """Возвращает JSON {link: ...}, фронт сам пишет в clipboard."""
    content = await get_ar_content_by_id(int(ar_content_id), db)
    if not content:
        raise HTTPException(status_code=404, detail="AR content not found")
    if hasattr(content, "model_dump"):
        content_data = content.model_dump()
    elif hasattr(content, "__dict__"):
        content_data = content.__dict__
    else:
        content_data = dict(content)
    unique_link = content_data.get("unique_link") or content_data.get("public_url") or ""
    link = unique_link
    if unique_link.startswith("/"):
        base = (settings.PUBLIC_URL or "").rstrip("/")
        link = f"{base}{unique_link}" if base else unique_link
    return {"link": link}


# ---------- 2. QR-CODE (с кешем) ----------
@router.get("/ar-content/{ar_content_id}/qr-code", response_class=HTMLResponse)
async def get_ar_content_qr_code(
    ar_content_id: str,
    request: Request,
    db: AsyncSession = Depends(get_html_db),
    current_user=CurrentActiveUser,
):
    content = await get_ar_content_by_id(int(ar_content_id), db)
    if not content:
        raise HTTPException(status_code=404, detail="AR content not found")
    if hasattr(content, "model_dump"):
        content_data = content.model_dump()
    elif hasattr(content, "__dict__"):
        content_data = content.__dict__
    else:
        content_data = dict(content)

    # Единый формат ссылки из PUBLIC_URL (для QR и приложения)
    public_url = content_data.get("unique_link") or content_data.get("public_url") or ""
    if public_url.startswith("/"):
        base = (settings.PUBLIC_URL or "").rstrip("/")
        public_url = f"{base}{public_url}" if base else public_url

    cache_key = f"qr:{ar_content_id}"
    cached = None
    try:
        cached = await redis_client.get(cache_key)
    except Exception:
        cached = None
    if cached:
        img_b64 = cached
    else:
        qr = qrcode.make(public_url, image_factory=qrcode.image.pil.PilImage)
        buf = io.BytesIO()
        qr.save(buf, format="PNG")
        buf.seek(0)
        img_b64 = base64.b64encode(buf.read()).decode()
        try:
            await redis_client.set(cache_key, img_b64, ex=QR_CACHE_TTL)
        except Exception:
            pass

    display_url = public_url if public_url else ""
    html = f"""
    <div class="flex flex-col items-center">
        <div class="bg-white p-4 rounded">
            <img src="data:image/png;base64,{img_b64}" alt="QR Code">
        </div>
        <p class="mt-2 text-sm break-all max-w-xs">{display_url}</p>
    </div>
    """
    return HTMLResponse(html)


# ---------- 3. DELETE (soft) ----------
@router.delete("/ar-content/{ar_content_id}", response_class=HTMLResponse)
async def delete_ar_content_fragment(
    ar_content_id: str,
    db: AsyncSession = Depends(get_html_db),
    current_user=CurrentActiveUser,
):
    content = await get_ar_content_by_id(int(ar_content_id), db)
    if not content:
        raise HTTPException(status_code=404, detail="AR content not found")
    await update_ar_content(
        int(ar_content_id),
        ARContentUpdate(status="deleted"),
        db,
        current_user,
    )
    # сброс кеша QR, если вдруг восстановят
    try:
        await redis_client.delete(f"qr:{ar_content_id}")
    except Exception:
        pass
    return HTMLResponse("")   # outerHTML удалит <tr>


# ---------- 4. UNDO (restore) ----------
@router.put("/ar-content/{ar_content_id}/restore", response_class=HTMLResponse)
async def restore_ar_content_fragment(
    ar_content_id: str,
    db: AsyncSession = Depends(get_html_db),
    current_user=CurrentActiveUser,
):
    content = await get_ar_content_by_id(int(ar_content_id), db)
    if not content:
        raise HTTPException(status_code=404, detail="AR content not found")
    await update_ar_content(
        int(ar_content_id),
        ARContentUpdate(status="active"),
        db,
        current_user,
    )
    # при желании можно вернуть целую новую <tr>-строку,
    # чтобы заменить «Удалено» на «Активно», но пока просто
    # убираем UNDO-блок
    return HTMLResponse("")   # убирает блок «Отменить»