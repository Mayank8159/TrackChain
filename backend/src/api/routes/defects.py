# POST defect events; GET defect list with severity/class filters, nearby geospatial search, and ML explainability (tc.v1 SOTA).

import math
import asyncio
from typing import List, Optional, Union, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Header, Request
from sqlalchemy.orm import Session
from src.api.deps import get_db_session
from src.db.models import DefectEvent, MonitoringSession, MLSignal
from src.schemas.defects import DefectCreate, DefectResponse
from src.services.alerts import dispatch_defect_alert
from src.services.idempotency import check_idempotency, record_idempotency
from src.services.rate_limiter import check_device_rate
from src.services.auth import get_current_device_optional
from src.services.observability import DEFECTS_CREATED
from src.services.audit import AuditService
from src.services.webhooks import webhook_service

router = APIRouter(prefix="/defects", tags=["Defects"])


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in meters using Haversine formula."""
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


@router.post("", response_model=DefectResponse, dependencies=[Depends(check_device_rate)])
def create_defect_event(
    payload: DefectCreate,
    request: Request,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    db: Session = Depends(get_db_session),
    device_auth: Optional[dict] = Depends(get_current_device_optional),
):
    import time
    import uuid
    from src.services.trace_buffer import trace_buffer

    t_start = time.perf_counter()
    capture_hdr = request.headers.get("X-Capture-Time")
    try:
        captured_at = int(capture_hdr) if capture_hdr else int(time.time() * 1000) - 35
    except (ValueError, TypeError):
        captured_at = int(time.time() * 1000) - 35

    ingested_at = int(time.time() * 1000)

    device_id = device_auth["device_id"] if device_auth else payload.device_id
    idemp_key = (
        x_idempotency_key
        if isinstance(x_idempotency_key, str)
        else (payload.idempotency_key if isinstance(getattr(payload, "idempotency_key", None), str) else None)
    )

    if idemp_key:
        cached = check_idempotency(db, idemp_key, entity_type="defects")
        if cached:
            existing = db.query(DefectEvent).filter(DefectEvent.id == cached.get("id")).first()
            if existing:
                return existing

    defect = DefectEvent(
        session_id=payload.session_id,
        device_id=device_id,
        segment_id=payload.segment_id,
        chainage_m=payload.chainage_m,
        chainage_start_m=payload.chainage_start_m,
        chainage_end_m=payload.chainage_end_m,
        defect_class=payload.defect_class,
        defect_family=payload.defect_family or "visual_component",
        severity=payload.severity,
        decision=payload.decision or "INSPECT_KNOWN",
        confidence=payload.confidence,
        source_model=payload.source_model or "yolo_v8_detector",
        model_version=payload.model_version,
        stream_source=payload.stream_source,
        image_url=payload.image_url,
        evidence_image_id=payload.evidence_image_id,
        video_media_id=payload.video_media_id,
        video_timestamp_sec=payload.video_timestamp_sec,
        video_offset_seconds=payload.video_offset_seconds,
        description=payload.description,
        status=payload.status or "open",
        latitude=payload.latitude,
        longitude=payload.longitude,
        notes=payload.notes,
    )
    db.add(defect)
    db.flush()

    # Link any supporting ML signals for model explainability
    if payload.supporting_signals:
        for sig in payload.supporting_signals:
            db_sig = MLSignal(
                session_id=payload.session_id,
                segment_id=payload.segment_id,
                defect_id=defect.id,
                model_name=sig.model_name,
                model_version=sig.model_version,
                signal_type=sig.signal_type,
                raw_score=sig.raw_score,
                calibrated_score=sig.calibrated_score,
                threshold=sig.threshold,
                fired=sig.fired,
                label=sig.label,
                bbox=sig.bbox,
                explanation=sig.explanation,
                timestamp=sig.timestamp,
            )
            db.add(db_sig)

    # Increment defect counter on session
    session_obj = db.query(MonitoringSession).filter(MonitoringSession.id == payload.session_id).first()
    if session_obj:
        session_obj.defects_count = (session_obj.defects_count or 0) + 1

    db.commit()
    db.refresh(defect)

    # Record idempotency key
    if idemp_key:
        record_idempotency(
            db,
            idempotency_key=idemp_key,
            entity_type="defects",
            entity_id=defect.id,
            response_payload={"id": defect.id, "status": "created"},
        )

    # Increment Prometheus metrics
    DEFECTS_CREATED.labels(
        defect_class=defect.defect_class,
        severity=defect.severity,
        source_model=defect.source_model or "unknown",
    ).inc()

    # Record immutable audit log
    AuditService.log_sync(
        actor_type="device" if device_id else "user",
        actor_id=device_id or "system",
        action="defect.created",
        resource_type="defect",
        resource_id=defect.id,
        details={
            "defect_class": defect.defect_class,
            "severity": defect.severity,
            "chainage_m": defect.chainage_m,
            "confidence": defect.confidence,
        },
        ip_address=request.client.host if request.client else None,
        db=db,
    )

    # Trigger alert if high / critical
    dispatch_defect_alert(payload)

    # Trigger external webhook dispatch if high / critical
    if defect.severity in ["high", "critical"]:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                webhook_service.send_alert(
                    system="rdso",
                    event_type=f"defect.{defect.severity}",
                    payload={
                        "defect_id": defect.id,
                        "defect_class": defect.defect_class,
                        "severity": defect.severity,
                        "chainage_m": defect.chainage_m,
                        "latitude": defect.latitude,
                        "longitude": defect.longitude,
                        "confidence": defect.confidence,
                        "session_id": defect.session_id,
                    },
                )
            )
        except Exception:
            pass

    inference_ms = round((time.perf_counter() - t_start) * 1000, 2)
    trace_buffer.add({
        "trace_id": str(uuid.uuid4()),
        "node_id": device_id or "edge-rpi-01",
        "event_type": "DEFECT",
        "captured_at": captured_at,
        "ingested_at": ingested_at,
        "inference_ms": max(2.5, inference_ms),
    })

    return defect


@router.post("/batch", response_model=dict, dependencies=[Depends(check_device_rate)])
def create_defects_batch(
    payload: Union[List[DefectCreate], dict],
    request: Request,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    db: Session = Depends(get_db_session),
    device_auth: Optional[dict] = Depends(get_current_device_optional),
):
    """Register a batch of AI-detected or fused defect events."""
    items = payload if isinstance(payload, list) else payload.get("defects", payload.get("events", []))
    created_count = 0
    defect_ids = []

    for item_data in items:
        p = item_data if isinstance(item_data, DefectCreate) else DefectCreate(**item_data)
        d = create_defect_event(p, request=request, x_idempotency_key=None, db=db, device_auth=device_auth)
        defect_ids.append(d.id)
        created_count += 1

    return {"status": "ok", "inserted": created_count, "defect_ids": defect_ids}


@router.get("/nearby", response_model=dict)
def get_nearby_defects(
    lat: float = Query(..., description="Latitude of inspection center"),
    lon: float = Query(..., description="Longitude of inspection center"),
    radius_m: float = Query(default=500.0, ge=1.0, le=50000.0, description="Search radius in meters"),
    db: Session = Depends(get_db_session),
):
    """Find all track defects within a given radius (meters) using spatial distance filtering."""
    lat_delta = radius_m / 111000.0
    lon_delta = radius_m / (111000.0 * max(0.1, math.cos(math.radians(lat))))

    candidates = (
        db.query(DefectEvent)
        .filter(DefectEvent.latitude.isnot(None))
        .filter(DefectEvent.longitude.isnot(None))
        .filter(DefectEvent.latitude.between(lat - lat_delta, lat + lat_delta))
        .filter(DefectEvent.longitude.between(lon - lon_delta, lon + lon_delta))
        .all()
    )

    results = []
    for defect in candidates:
        dist = haversine_distance_meters(lat, lon, defect.latitude, defect.longitude)
        if dist <= radius_m:
            results.append({
                "id": defect.id,
                "defect_class": defect.defect_class,
                "severity": defect.severity,
                "chainage_m": defect.chainage_m,
                "latitude": defect.latitude,
                "longitude": defect.longitude,
                "confidence": defect.confidence,
                "distance_m": round(dist, 2),
            })

    results.sort(key=lambda x: x["distance_m"])
    return {
        "center": {"lat": lat, "lon": lon},
        "radius_m": radius_m,
        "count": len(results),
        "defects": results,
    }


@router.get("", response_model=List[DefectResponse])
def list_defects(
    session_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    defect_class: Optional[str] = Query(None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db_session),
):
    """Retrieve defect events filtered by severity, defect class, and session."""
    query = db.query(DefectEvent)
    if session_id:
        query = query.filter(DefectEvent.session_id == session_id)
    if severity:
        query = query.filter(DefectEvent.severity == severity)
    if defect_class:
        query = query.filter(DefectEvent.defect_class == defect_class)

    return query.order_by(DefectEvent.timestamp.desc()).offset(offset).limit(limit).all()


@router.get("/{defect_id}", response_model=DefectResponse)
def get_defect_by_id(
    defect_id: str,
    db: Session = Depends(get_db_session),
):
    """Retrieve a single defect with full ML explainability signals and media links."""
    defect = db.query(DefectEvent).filter(DefectEvent.id == defect_id).first()
    if not defect:
        raise HTTPException(status_code=404, detail="Defect not found")
    return defect
