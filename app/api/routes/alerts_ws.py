import asyncio
import json
from urllib.parse import urlparse

import structlog
from fastapi import APIRouter, WebSocket
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import (
    decode_token,
    is_token_blacklisted,
    is_user_revoked,
)

router = APIRouter()
logger = structlog.get_logger()


def _is_allowed_origin(ws: WebSocket) -> bool:
    """Validate the ``Origin`` header to prevent Cross-Site WebSocket Hijacking.

    Browsers always send ``Origin`` on a WebSocket handshake. A missing header
    means a non-browser client (e.g. the Android app), which cannot be hijacked
    through ambient credentials, so it is allowed.

    A present ``Origin`` must match one of the configured CORS origins, the
    configured PUBLIC_URL, or the ``Host`` the client connected to.
    """
    origin = ws.headers.get("origin")
    if not origin:
        return True

    settings = get_settings()
    origin = origin.rstrip("/")

    allowed = {str(o).rstrip("/") for o in (settings.CORS_ORIGINS or [])}
    if settings.PUBLIC_URL:
        allowed.add(str(settings.PUBLIC_URL).rstrip("/"))

    if origin in allowed:
        return True

    # Same-host fallback: compare scheme+host+port of Origin against Host header.
    try:
        parsed = urlparse(origin)
        host = ws.headers.get("host", "")
        if parsed.netloc and host and parsed.netloc == host:
            return True
    except ValueError:
        pass

    return False


@router.websocket("/ws/alerts")
async def alerts_websocket(ws: WebSocket):
    """Live alerts channel.

    Token sources, in order of preference:
      1. ``access_token`` cookie (HttpOnly, set by the HTML login flow) —
         never touches the URL, so it cannot leak into access logs/history.
      2. ``?token=`` query parameter — DEPRECATED, kept for backward
         compatibility with existing mobile clients. Migrate away from it.
    """
    if not _is_allowed_origin(ws):
        logger.warning("alerts_ws_origin_rejected", origin=ws.headers.get("origin"))
        await ws.accept()
        await ws.close(code=1008, reason="Origin not allowed")
        return

    token = ws.cookies.get("access_token") or ws.query_params.get("token")
    if not token:
        await ws.accept()
        await ws.close(code=1008, reason="Authentication required")
        return

    payload = decode_token(token)
    if not payload:
        await ws.accept()
        await ws.close(code=1008, reason="Authentication required")
        return

    # Honour explicit revocation (logout / admin-forced invalidation).
    if await is_token_blacklisted(token):
        await ws.accept()
        await ws.close(code=1008, reason="Token revoked")
        return

    email = payload.get("sub")
    if not email:
        await ws.accept()
        await ws.close(code=1008, reason="Invalid token payload")
        return

    from app.core.database import AsyncSessionLocal
    from app.models.user import User

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            await ws.accept()
            await ws.close(code=1008, reason="Inactive user or not authenticated")
            return

        if await is_user_revoked(user.id):
            await ws.accept()
            await ws.close(code=1008, reason="Session revoked")
            return

    await ws.accept()
    logger.info("alerts_ws_connected", user_id=user.id)

    try:
        while True:
            await ws.send_text(json.dumps({"type": "keepalive"}))
            await asyncio.sleep(10.0)
    except Exception as e:
        logger.error("alerts_ws_error", error=str(e))
    finally:
        await ws.close()
