# Alert dispatch and async SSE event queue broker (tc.v1 SOTA).

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

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
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    for q in _subscribers:
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            dead_queues.append(q)

    for dq in dead_queues:
        unregister_subscriber(dq)


async def broadcast_alert(defect_event: Dict[str, Any]):
    """Async broadcast method for critical and high defect alerts."""
    await broadcast_event("defect_alert", defect_event)


def dispatch_defect_alert(defect: Any):
    """Dispatch instant notifications for high and critical railway defects."""
    if hasattr(defect, "severity") and str(defect.severity).lower() in ["high", "critical"]:
        class_name = getattr(defect, "defect_class", "anomaly")
        chainage = getattr(defect, "chainage_m", 0.0)
        conf = getattr(defect, "confidence", 0.0)
        session_id = getattr(defect, "session_id", "unknown")
        severity_val = getattr(defect, "severity", "high")

        logger.warning(
            f"[ALERT] CRITICAL RAILWAY DEFECT ALERT: [{str(class_name).upper()}] "
            f"detected at Chainage {(float(chainage) / 1000):.3f} km. "
            f"Confidence: {float(conf):.2%}. Session: {session_id}"
        )

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    broadcast_event(
                        "defect_alert",
                        {
                            "defect_class": str(class_name),
                            "severity": str(severity_val),
                            "chainage_m": float(chainage),
                            "confidence": float(conf),
                            "session_id": str(session_id),
                        },
                    )
                )
        except Exception:
            pass

        return True
    return False
