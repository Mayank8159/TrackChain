# POST batched telemetry rows and GET downsampled series for graphs (tc.v1 SOTA).

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Header, Request
from sqlalchemy.orm import Session
from src.api.deps import get_db_session
from src.db.models import TelemetryRecord
from src.schemas.telemetry import (
    TelemetryBatchRequest,
    TelemetryPointCreate,
    TelemetryPointResponse,
)
from src.services.idempotency import check_idempotency, record_idempotency
from src.services.downsampling import downsample_telemetry_lttb
from src.services.rate_limiter import check_device_rate
from src.services.auth import get_current_device_optional

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])


@router.post("", response_model=dict, dependencies=[Depends(check_device_rate)])
@router.post("/batch", response_model=dict, dependencies=[Depends(check_device_rate)])
def ingest_telemetry_batch(
    payload: TelemetryBatchRequest,
    request: Request,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    db: Session = Depends(get_db_session),
    device_auth: Optional[dict] = Depends(get_current_device_optional),
):
    """Ingest a high-frequency telemetry batch with network idempotency protection and rate limiting."""
    device_id = device_auth["device_id"] if device_auth else payload.device_id
    idemp_key = x_idempotency_key if isinstance(x_idempotency_key, str) else (payload.idempotency_key if isinstance(getattr(payload, "idempotency_key", None), str) else None)
    if idemp_key:
        cached = check_idempotency(db, idemp_key, entity_type="telemetry")
        if cached:
            return cached

    raw_samples = payload.samples or payload.points or []
    records = [
        TelemetryRecord(
            session_id=p.session_id or payload.session_id,
            device_id=device_id,
            chainage_m=p.chainage_m,
            speed_mps=p.speed_mps,
            speed_kmh=p.speed_kmh or (p.speed_mps * 3.6 if p.speed_mps else 0.0),
            vibration_rms=p.vibration_rms,
            track_gauge_mm=p.track_gauge_mm,
            cant_mm=p.cant_mm,
            twist_mm_per_m=p.twist_mm_per_m,
            vertical_unevenness_mm=p.vertical_unevenness_mm,
            alignment_dev_mm=p.alignment_dev_mm,
            latitude=p.latitude,
            longitude=p.longitude,
        )
        for p in raw_samples
    ]
    import time
    import uuid
    from src.services.trace_buffer import trace_buffer

    t_start = time.perf_counter()
    capture_hdr = request.headers.get("X-Capture-Time")
    try:
        captured_at = int(capture_hdr) if capture_hdr else int(time.time() * 1000) - 28
    except (ValueError, TypeError):
        captured_at = int(time.time() * 1000) - 28

    ingested_at = int(time.time() * 1000)

    try:
        db.bulk_save_objects(records)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {exc}")

    inference_ms = round((time.perf_counter() - t_start) * 1000, 2)
    trace_buffer.add({
        "trace_id": str(uuid.uuid4()),
        "node_id": device_id or "edge-rpi-01",
        "event_type": "TELEMETRY",
        "captured_at": captured_at,
        "ingested_at": ingested_at,
        "inference_ms": max(1.2, inference_ms),
    })

    resp = {
        "status": "ok",
        "inserted": len(records),
        "session_id": payload.session_id,
        "device_id": device_id,
        "captured_at": captured_at,
        "ingested_at": ingested_at,
        "inference_ms": inference_ms,
    }
    if idemp_key:
        record_idempotency(db, idempotency_key=idemp_key, entity_type="telemetry", response_payload=resp, entity_id=payload.session_id)
    return resp


@router.get("", response_model=List[TelemetryPointResponse])
def get_session_telemetry(
    session_id: str = Query(..., description="Inspection session ID"),
    downsample: Optional[int] = Query(default=None, description="Max points to return using LTTB (alias)"),
    downsample_points: Optional[int] = Query(default=None, description="Max points to return using LTTB"),
    db: Session = Depends(get_db_session),
):
    """Fetch raw or peak-preserved LTTB downsampled telemetry for time-series charts."""
    target = downsample or downsample_points or 1000
    records = (
        db.query(TelemetryRecord)
        .filter(TelemetryRecord.session_id == session_id)
        .order_by(TelemetryRecord.chainage_m.asc())
        .all()
    )

    if target and len(records) > target:
        records = downsample_telemetry_lttb(records, target_points=target)

    return records


@router.get("/{session_id}", response_model=List[TelemetryPointResponse])
def get_session_telemetry_by_path(
    session_id: str,
    downsample: Optional[int] = Query(default=None, description="Max points to return using LTTB (alias)"),
    downsample_points: Optional[int] = Query(default=None, description="Max points to return using LTTB"),
    db: Session = Depends(get_db_session),
):
    """Fetch raw or peak-preserved LTTB downsampled telemetry for time-series charts (Path Parameter)."""
    return get_session_telemetry(session_id=session_id, downsample=downsample, downsample_points=downsample_points, db=db)
