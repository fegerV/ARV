import asyncio
import json
import structlog
from fastapi import APIRouter, WebSocket

router = APIRouter()
logger = structlog.get_logger()


@router.websocket("/ws/alerts")
async def alerts_websocket(ws: WebSocket):
    await ws.accept()
    logger.info("alerts_ws_connected")

    try:
        while True:
            await ws.send_text(json.dumps({"type": "keepalive"}))
            await asyncio.sleep(10.0)
    except Exception as e:
        logger.error("alerts_ws_error", error=str(e))
    finally:
        await ws.close()
