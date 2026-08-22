from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Any
from src.services import auth

router = APIRouter()

# Defer imports of ingest to avoid circular deps if needed
_ingest_service = None

def get_ingest_service():
    global _ingest_service
    if _ingest_service is None:
        from src.services import ingest
        _ingest_service = ingest
    return _ingest_service

@router.websocket("/ws/node")
async def node_gateway(ws: WebSocket):
    token = ws.query_params.get("token", "")
    
    # In a real system, verify HMAC vs DB-issued tokens.
    # For now, we mock auth or allow generic "SECRET_TOKEN"
    if not token or token != "SECRET_TOKEN":
        await ws.close(code=4001)
        return
        
    # Mock node object for now
    class Node:
        def __init__(self, node_id):
            self.id = node_id
    node = Node("TC-NODE-01")
            
    await ws.accept()
    ingest = get_ingest_service()
    
    try:
        while True:
            msg = await ws.receive_json()
            kind = msg.get("type")
            if kind == "imu":
                await ingest.push_imu(node.id, msg)
            elif kind == "frame":
                await ingest.push_frame(node.id, msg)
            elif kind == "hb":
                await ws.send_json({"type": "ack", "t": msg.get("t")})
            elif kind == "hello":
                node.id = msg.get("node_id", node.id)
                print(f"Node {node.id} connected via WebSocket")
    except WebSocketDisconnect:
        await ingest.node_offline(node.id)
    except Exception as e:
        print(f"Node WS Error: {e}")
        try:
            await ws.close(code=1011)
        except:
            pass
