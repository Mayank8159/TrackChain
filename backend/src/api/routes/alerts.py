# Server-Sent Events (SSE) route for real-time SCADA alerts (tc.v1 SOTA).

import asyncio
import json
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from src.services.alerts import register_subscriber, unregister_subscriber

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


@router.get("/stream")
async def stream_alerts(request: Request):
    """
    Server-Sent Events endpoint streaming live defect events and alarms to the UI.
    Eliminates manual polling and guarantees instantaneous display of critical track faults.
    """
    q = register_subscriber()

    async def event_generator():
        try:
            # Yield initial connection confirmation
            yield f"event: ping\ndata: {json.dumps({'status': 'connected'})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    # Wait up to 15s for new alert or send keepalive ping
                    payload = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield f"event: {payload['event']}\ndata: {json.dumps(payload['data'])}\n\n"
                except asyncio.TimeoutError:
                    yield f"event: ping\ndata: {json.dumps({'keepalive': True})}\n\n"
        finally:
            unregister_subscriber(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
