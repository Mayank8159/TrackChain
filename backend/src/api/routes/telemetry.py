# POST batched telemetry rows and GET downsampled series for graphs.

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from src.api.deps import get_db_session
from src.db.models import TelemetryRecord
from src.schemas.telemetry import (
    TelemetryBatchRequest,
    TelemetryPointCreate,
    TelemetryPointResponse,
)

router = APIRouter(prefix="/api/telemetry", tags=["Telemetry"])


@router.post("", response_model=dict)
def ingest_telemetry_batch(
    payload: TelemetryBatchRequest,
    db: Session = Depends(get_db_session),
):
    """Ingest a high-frequency telemetry batch from edge car inspection sensors."""
    records = [
        TelemetryRecord(
            session_id=p.session_id,
            chainage_m=p.chainage_m,
            speed_kmh=p.speed_kmh,
            vibration_rms=p.vibration_rms,
            track_gauge_mm=p.track_gauge_mm,
            cant_mm=p.cant_mm,
            twist_mm_per_m=p.twist_mm_per_m,
            vertical_unevenness_mm=p.vertical_unevenness_mm,
            alignment_dev_mm=p.alignment_dev_mm,
            latitude=p.latitude,
            longitude=p.longitude,
        )
        for p in payload.points
    ]
    try:
        db.bulk_save_objects(records)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {exc}")

    return {"status": "ok", "inserted": len(records)}


@router.get("", response_model=List[TelemetryPointResponse])
def get_telemetry_series(
    session_id: str = Query(..., description="Session identifier"),
    downsample: int = Query(default=100, description="Step downsampling factor"),
    limit: int = Query(default=500, le=2000),
    db: Session = Depends(get_db_session),
):
    """Fetch time-series telemetry downsampled for graph rendering."""
    query = (
        db.query(TelemetryRecord)
        .filter(TelemetryRecord.session_id == session_id)
        .order_by(TelemetryRecord.chainage_m.asc())
    )
    records = query.limit(limit).all()
    # Downsample on step
    if downsample > 1 and len(records) > downsample:
        step = max(1, len(records) // downsample)
        records = records[::step]
    return records
