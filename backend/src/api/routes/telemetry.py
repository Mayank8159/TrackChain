# POST batched telemetry rows and GET downsampled series for graphs (tc.v1 SOTA).

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Header
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

router = APIRouter(prefix="/api/telemetry", tags=["Telemetry"])


@router.post("", response_model=dict)
def ingest_telemetry_batch(
    payload: TelemetryBatchRequest,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    db: Session = Depends(get_db_session),
):
    """Ingest a high-frequency telemetry batch with network idempotency protection."""
    idemp_key = x_idempotency_key or payload.idempotency_key
    cached = check_idempotency(db, idemp_key, entity_type="telemetry")
    if cached:
        return cached

    raw_samples = payload.samples or payload.points or []
    records = [
        TelemetryRecord(
            session_id=p.session_id or payload.session_id,
            device_id=payload.device_id,
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
    try:
        db.bulk_save_objects(records)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {exc}")

    resp = {"status": "ok", "inserted": len(records), "session_id": payload.session_id}
    if idemp_key:
        record_idempotency(
            db,
            idempotency_key=idemp_key,
            entity_type="telemetry",
            entity_id=payload.session_id,
            response_payload=resp,
        )

    return resp


@router.get("", response_model=List[TelemetryPointResponse])
def get_telemetry_series(
    session_id: str = Query(..., description="Session identifier"),
    downsample: int = Query(default=500, description="LTTB downsampling target point count"),
    limit: int = Query(default=2000, le=10000),
    db: Session = Depends(get_db_session),
):
    """Fetch time-series telemetry with peak-preserving LTTB downsampling."""
    query = (
        db.query(TelemetryRecord)
        .filter(TelemetryRecord.session_id == session_id)
        .order_by(TelemetryRecord.chainage_m.asc())
    )
    records = query.limit(limit).all()
    if len(records) > downsample:
        records = downsample_telemetry_lttb(records, threshold=downsample)
    return records
