from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Any
from src.services.auth import verify_node_token

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
    
    node_id = verify_node_token(token)
    if not node_id:
        await ws.close(code=4001, reason="Unauthorized")
        return
            
    await ws.accept()
    ingest = get_ingest_service()
    
    try:
        while True:
            msg = await ws.receive_json()
            kind = msg.get("type")
            if kind == "hello":
                node_id = msg.get("node_id", node_id)
                print(f"Node {node_id} capabilities: {msg.get('caps', {})}")
                # Send initial adaptive config
                await ws.send_json({"type": "cfg", "fps": 5, "imu_hz": 20})
            elif kind == "frame":
                await ingest.push_frame(node_id, msg)
            elif kind == "imu":
                await ingest.push_imu(node_id, msg)
            elif kind == "hb":
                # Heartbeat acknowledgment and update last_seen (simulated)
                await ws.send_json({"type": "ack", "t": msg.get("t")})
    except WebSocketDisconnect:
        await ingest.node_offline(node_id)
    except Exception as e:
        print(f"Node WS Error: {e}")
        try:
            await ws.close(code=1011)
        except:
            pass
