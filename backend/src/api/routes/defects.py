# POST defect events; GET defect list with severity/class filters and ML explainability (tc.v1 SOTA).

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from src.api.deps import get_db_session
from src.db.models import DefectEvent, MonitoringSession, MLSignal
from src.schemas.defects import DefectCreate, DefectResponse
from src.services.alerts import dispatch_defect_alert
from src.services.idempotency import check_idempotency, record_idempotency

router = APIRouter(prefix="/api/defects", tags=["Defects"])


@router.post("", response_model=DefectResponse)
def create_defect_event(
    payload: DefectCreate,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    db: Session = Depends(get_db_session),
):
    """Register a new AI-detected or fused defect event with idempotency and ML signals."""
    idemp_key = x_idempotency_key or payload.idempotency_key
    cached = check_idempotency(db, idemp_key, entity_type="defects")
    if cached:
        existing = db.query(DefectEvent).filter(DefectEvent.id == cached.get("id")).first()
        if existing:
            return existing

    defect = DefectEvent(
        session_id=payload.session_id,
        device_id=payload.device_id,
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

    # Trigger alert if high / critical
    dispatch_defect_alert(payload)

    return defect


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
