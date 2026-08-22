import base64
import asyncio
from typing import Dict, Any
from .chainage import tracker
from .s3 import get_storage_service

# Global queues for the ML pipeline
frame_q = asyncio.Queue()
imu_q = asyncio.Queue()

class FrameSample:
    def __init__(self, node_id: str, t: float, chainage: float, key: str, raw: bytes):
        self.node_id = node_id
        self.t = t
        self.chainage = chainage
        self.key = key
        self.raw = raw

class ImuSample:
    def __init__(self, node_id: str, t: float, chainage: float, ax: float, ay: float, az: float, gx: float, gy: float, gz: float):
        self.node_id = node_id
        self.t = t
        self.chainage = chainage
        self.ax = ax
        self.ay = ay
        self.az = az
        self.gx = gx
        self.gy = gy
        self.gz = gz

async def push_frame(node_id: str, msg: Dict[str, Any]):
    raw = base64.b64decode(msg["b64"])
    ch = tracker.update(node_id, msg["t"], msg.get("speed"))
    key = f"{node_id}/{tracker.session(node_id)}/{msg['seq']}.jpg"
    
    # Store frame in S3 asynchronously
    storage = get_storage_service()
    
    # In a real app, this would be an async boto3 wrapper, e.g., aioboto3.
    # For now we'll simulate by wrapping the blocking call.
    loop = asyncio.get_event_loop()
    if hasattr(storage, "generate_presigned_put"):
        # LocalStorageService mock
        pass
        
    await frame_q.put(FrameSample(node_id, msg["t"], ch, key, raw))

async def push_imu(node_id: str, msg: Dict[str, Any]):
    ch = tracker.peek(node_id)
    await imu_q.put(ImuSample(
        node_id, msg["t"], ch,
        ax=msg["ax"], ay=msg["ay"], az=msg["az"],
        gx=msg["gx"], gy=msg["gy"], gz=msg["gz"]
    ))

async def node_offline(node_id: str):
    print(f"Node {node_id} went offline")
