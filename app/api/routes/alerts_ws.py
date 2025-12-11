import asyncio
import json
import structlog
import redis.asyncio as redis
from fastapi import APIRouter, WebSocket

from app.core.config import settings

router = APIRouter(prefix="/ws", tags=["WebSocket"])
logger = structlog.get_logger()


@router.websocket("/ws/alerts")
async def alerts_websocket(ws: WebSocket):
    await ws.accept()
    logger.info("alerts_ws_connected")

    r = redis.from_url(settings.REDIS_URL)
    pubsub = r.pubsub()
    await pubsub.subscribe("alerts")

    try:
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=5.0)
            if msg and msg.get("type") == "message":
                data = msg.get("data")
                try:
                    text = data.decode() if isinstance(data, (bytes, bytearray)) else str(data)
                    await ws.send_text(text)
                except Exception:
                    await ws.send_text(json.dumps({"title": "Alert", "message": str(data)}))
            await asyncio.sleep(0.1)
    except Exception as e:
        logger.error("alerts_ws_error", error=str(e))
    finally:
        try:
            await pubsub.unsubscribe("alerts")
            await pubsub.close()
            await r.aclose()
        except Exception:
            pass
        await ws.close()
