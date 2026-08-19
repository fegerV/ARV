import asyncio
import json
import structlog
from fastapi import APIRouter, WebSocket, HTTPException
from app.core.security import decode_token
from app.api.routes.auth import get_current_active_user

router = APIRouter()
logger = structlog.get_logger()


@router.websocket("/ws/alerts")
async def alerts_websocket(ws: WebSocket):
    token = ws.query_params.get("token")
    payload = decode_token(token) if token else None
    if not payload:
        await ws.accept()
        await ws.close(code=1008, reason="Authentication required")
        return

    email = payload.get("sub")
    if not email:
        await ws.accept()
        await ws.close(code=1008, reason="Invalid token payload")
        return

    from app.core.database import AsyncSessionLocal
    from sqlalchemy import select
    from app.models.user import User

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            await ws.accept()
            await ws.close(code=1008, reason="Inactive user or not authenticated")
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
