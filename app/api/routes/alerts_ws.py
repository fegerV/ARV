from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict
import json
import asyncio
import structlog

router = APIRouter()
logger = structlog.get_logger()

# Store active WebSocket connections
active_connections: Dict[str, List[WebSocket]] = {
    "global": [],
    "company": {}
}


async def broadcast_alert(alert_data: dict, company_id: str = "global"):
    """Broadcast alert to all connected clients for a specific company or globally."""
    connections = active_connections.get(company_id, []) if company_id != "global" else active_connections["global"]
    
    # Send to all connections for this company/global
    disconnected = []
    for connection in connections:
        try:
            await connection.send_text(json.dumps(alert_data))
        except WebSocketDisconnect:
            disconnected.append(connection)
        except Exception as e:
            logger.error("websocket_broadcast_error", error=str(e))
            disconnected.append(connection)
    
    # Remove disconnected clients
    for connection in disconnected:
        if connection in connections:
            connections.remove(connection)


@router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """Global alerts WebSocket endpoint."""
    await websocket.accept()
    active_connections["global"].append(websocket)
    logger.info("websocket_connected", client="global")
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("websocket_disconnected", client="global")
    finally:
        if websocket in active_connections["global"]:
            active_connections["global"].remove(websocket)


@router.websocket("/ws/alerts/company/{company_id}")
async def websocket_company_alerts(websocket: WebSocket, company_id: int):
    """Company-specific alerts WebSocket endpoint."""
    company_key = str(company_id)
    await websocket.accept()
    
    if company_key not in active_connections["company"]:
        active_connections["company"][company_key] = []
    
    active_connections["company"][company_key].append(websocket)
    logger.info("websocket_connected", client=f"company_{company_id}")
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("websocket_disconnected", client=f"company_{company_id}")
    finally:
        if websocket in active_connections["company"].get(company_key, []):
            active_connections["company"][company_key].remove(websocket)
            if not active_connections["company"][company_key]:
                del active_connections["company"][company_key]


@router.websocket("/ws/analytics")
async def websocket_analytics(websocket: WebSocket):
    """Global analytics WebSocket endpoint."""
    await websocket.accept()
    active_connections["global"].append(websocket)
    logger.info("websocket_connected", client="analytics_global")
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("websocket_disconnected", client="analytics_global")
    finally:
        if websocket in active_connections["global"]:
            active_connections["global"].remove(websocket)


@router.websocket("/ws/analytics/company/{company_id}")
async def websocket_company_analytics(websocket: WebSocket, company_id: int):
    """Company-specific analytics WebSocket endpoint."""
    company_key = str(company_id)
    await websocket.accept()
    
    if company_key not in active_connections["company"]:
        active_connections["company"][company_key] = []
    
    active_connections["company"][company_key].append(websocket)
    logger.info("websocket_connected", client=f"analytics_company_{company_id}")
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("websocket_disconnected", client=f"analytics_company_{company_id}")
    finally:
        if websocket in active_connections["company"].get(company_key, []):
            active_connections["company"][company_key].remove(websocket)
            if not active_connections["company"][company_key]:
                del active_connections["company"][company_key]


async def broadcast_analytics_event(event_data: dict, company_id: int = None):
    """Broadcast analytics event to WebSocket clients."""
    # Broadcast to global analytics listeners
    await broadcast_alert(event_data, "global")
    
    # If company_id is specified, also broadcast to company-specific listeners
    if company_id:
        await broadcast_alert(event_data, str(company_id))