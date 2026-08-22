from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio

router = APIRouter()

# Global list of active connections for broadcasting
_live_connections = []

@router.websocket("/ws/live")
async def live_gateway(ws: WebSocket, session: str = None):
    await ws.accept()
    _live_connections.append(ws)
    try:
        while True:
            # We don't expect the frontend to send much, maybe ping/pong
            msg = await ws.receive_json()
    except WebSocketDisconnect:
        if ws in _live_connections:
            _live_connections.remove(ws)

async def broadcast_live_event(event_dict: dict):
    """Called by the pipeline to broadcast frames/telemetry to all connected dashboards."""
    disconnected = []
    for ws in _live_connections:
        try:
            await ws.send_json(event_dict)
        except Exception:
            disconnected.append(ws)
            
    for ws in disconnected:
        if ws in _live_connections:
            _live_connections.remove(ws)
