# ML signals and segment decisions ingestion route (tc.v1).

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from src.api.deps import get_db_session
from src.db.models import MLSignal
from src.schemas.ml import (
    MLSignalCreate,
    MLSignalResponse,
    MLSignalBatchRequest,
)

router = APIRouter(prefix="/ml", tags=["ML Signals"])


@router.post("/signals/batch", response_model=dict)
def ingest_ml_signals_batch(
    payload: MLSignalBatchRequest,
    db: Session = Depends(get_db_session),
):
    """Ingest a batch of model signals and detections for a track segment."""
    records = [
        MLSignal(
            session_id=payload.session_id,
            segment_id=payload.segment_id,
            model_name=s.model_name,
            model_version=s.model_version,
            signal_type=s.signal_type,
            raw_score=s.raw_score,
            calibrated_score=s.calibrated_score,
            threshold=s.threshold,
            fired=s.fired,
            label=s.label,
            bbox=s.bbox,
            explanation=s.explanation,
            timestamp=s.timestamp,
        )
        for s in payload.signals
    ]
    try:
        db.bulk_save_objects(records)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {exc}")

    return {"status": "ok", "inserted": len(records), "segment_id": payload.segment_id}


@router.get("/signals", response_model=List[MLSignalResponse])
def get_ml_signals(
    session_id: str = Query(..., description="Session identifier"),
    segment_id: str = Query(None, description="Segment identifier"),
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db_session),
):
    """Fetch model signals for explainability and calibration audit."""
    query = db.query(MLSignal).filter(MLSignal.session_id == session_id)
    if segment_id:
        query = query.filter(MLSignal.segment_id == segment_id)
    return query.order_by(MLSignal.timestamp.desc()).limit(limit).all()
