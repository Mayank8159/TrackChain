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


def dispatch_device_discovered(device: Any, lat: Optional[float] = None, lon: Optional[float] = None):
    """Dispatch instant SSE event when a new edge node is auto-discovered on the network."""
    dev_id = getattr(device, "device_id", "unknown")
    dev_name = getattr(device, "device_name", f"Edge Node {dev_id}")
    hw = getattr(device, "hardware_version", "Raspberry Pi 5")
    fw = getattr(device, "firmware_version", "v1.0.0")
    cam = getattr(device, "camera_model", "Sony IMX477 (Auto-Discovered)")
    dev_status = getattr(device, "status", "pending_approval")

    logger.info(f"[AUTO-DISCOVERY] New Edge Node Materialized: [{dev_id}] - {dev_name} (Lat: {lat}, Lon: {lon})")

    payload = {
        "device_id": str(dev_id),
        "deviceId": str(dev_id),
        "device_name": str(dev_name),
        "deviceName": str(dev_name),
        "hardware_version": str(hw),
        "hardwareVersion": str(hw),
        "firmware_version": str(fw),
        "firmwareVersion": str(fw),
        "camera_model": cam,
        "cameraModel": cam,
        "status": str(dev_status),
        "latitude": lat,
        "longitude": lon,
        "is_discovered": True,
        "isDiscovered": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(broadcast_event("device_discovered", payload))
    except Exception as exc:
        logger.warning(f"Could not dispatch device_discovered event: {exc}")

    return payload

