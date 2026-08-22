import base64
import asyncio
from typing import Dict, Any
from .chainage import tracker
from .s3 import get_storage_service

# Global queues for the ML pipeline
frame_q = asyncio.Queue()
imu_q = asyncio.Queue()



async def push_frame(node_id: str, msg: Dict[str, Any]):
    raw = base64.b64decode(msg["b64"])
    ch = tracker.update(node_id, msg["t"], msg.get("speed"))
    key = f"frames/{node_id}/{tracker.session(node_id)}/{msg['seq']}.jpg"
    
    # Store frame in S3 asynchronously
    storage = get_storage_service()
    if hasattr(storage, "async_upload_bytes"):
        asyncio.create_task(storage.async_upload_bytes(raw, key))
        
    await frame_q.put({
        "node_id": node_id,
        "t": msg["t"],
        "seq": msg.get("seq", 0),
        "bytes": raw,
        "s3_key": key,
        "chainage": ch,
        "w": msg.get("w", 0),
        "h": msg.get("h", 0)
    })

async def push_imu(node_id: str, msg: Dict[str, Any]):
    ch = tracker.peek(node_id)
    await imu_q.put({
        "node_id": node_id,
        "t": msg["t"],
        "seq": msg.get("seq", 0),
        "chainage": ch,
        "ax": msg.get("ax", 0), "ay": msg.get("ay", 0), "az": msg.get("az", 0),
        "gx": msg.get("gx", 0), "gy": msg.get("gy", 0), "gz": msg.get("gz", 0)
    })

async def node_offline(node_id: str):
    print(f"Node {node_id} went offline")
