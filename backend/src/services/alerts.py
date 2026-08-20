# Alert dispatch and async SSE event queue broker (tc.v1 SOTA).

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger("trackchain.alerts")

# In-memory async subscribers list for live SSE streaming
_subscribers: List[asyncio.Queue] = []


def register_subscriber() -> asyncio.Queue:
    """Register a new SSE stream client."""
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers.append(q)
    return q


def unregister_subscriber(q: asyncio.Queue):
    """Unregister an SSE stream client upon disconnect."""
    if q in _subscribers:
        _subscribers.remove(q)


async def broadcast_event(event_type: str, data: Dict[str, Any]):
    """Broadcast an event to all active SSE subscribers."""
    dead_queues = []
    payload = {
        "event": event_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat(),
    }
    for q in _subscribers:
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            dead_queues.append(q)

    for dq in dead_queues:
        unregister_subscriber(dq)


def dispatch_defect_alert(defect: Any):
    """Dispatch instant notifications for high and critical railway defects."""
    if hasattr(defect, "severity") and defect.severity in ["high", "critical"]:
        class_name = getattr(defect, "defect_class", "anomaly")
        chainage = getattr(defect, "chainage_m", 0.0)
        conf = getattr(defect, "confidence", 0.0)
        session_id = getattr(defect, "session_id", "unknown")

        logger.warning(
            f"[ALERT] CRITICAL RAILWAY DEFECT ALERT: [{class_name.upper()}] "
            f"detected at Chainage {(chainage / 1000):.3f} km. "
            f"Confidence: {conf:.2%}. Session: {session_id}"
        )

        # Trigger async broadcast in running event loop if active
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    broadcast_event(
                        "defect_alert",
                        {
                            "defect_class": class_name,
                            "severity": defect.severity,
                            "chainage_m": chainage,
                            "confidence": conf,
                            "session_id": session_id,
                        },
                    )
                )
        except Exception:
            pass

        return True
    return False
