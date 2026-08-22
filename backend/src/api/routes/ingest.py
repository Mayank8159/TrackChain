from fastapi import APIRouter, Header, HTTPException, Request
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

router = APIRouter(tags=["Ingest"])

class BatchIngestPayload(BaseModel):
    node_id: str
    imu: List[Dict[str, Any]] = []
    frames: List[Dict[str, Any]] = []

@router.post("/ingest/batch", status_code=202)
async def ingest_batch(
    payload: BatchIngestPayload, 
    x_idempotency_key: str = Header(...)
):
    """
    Store-and-forward fallback endpoint for nodes when WebSocket connection is unavailable.
    Uses idempotency keys to prevent duplicate processing of the same batch.
    """
    from src.services import idempotency
    
    # Check idempotency
    if idempotency.is_duplicate(x_idempotency_key):
        return {"status": "accepted", "duplicate": True}
        
    from src.services import ingest
    
    # Process IMU
    for imu_msg in payload.imu:
        # Re-construct expected msg format
        msg = {"type": "imu", **imu_msg}
        await ingest.push_imu(payload.node_id, msg)
        
    # Process frames
    for frame_msg in payload.frames:
        msg = {"type": "frame", **frame_msg}
        await ingest.push_frame(payload.node_id, msg)
        
    idempotency.mark_processed(x_idempotency_key)
    return {"status": "accepted", "processed_imu": len(payload.imu), "processed_frames": len(payload.frames)}
