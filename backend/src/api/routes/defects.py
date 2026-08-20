# POST defect events; GET defect list with severity/class filters.

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from src.api.deps import get_db_session
from src.db.models import DefectEvent, MonitoringSession
from src.schemas.defects import DefectCreate, DefectResponse
from src.services.alerts import dispatch_defect_alert

router = APIRouter(prefix="/api/defects", tags=["Defects"])


@router.post("", response_model=DefectResponse)
def create_defect_event(
    payload: DefectCreate,
    db: Session = Depends(get_db_session),
):
    """Register a new AI-detected or fused defect event."""
    defect = DefectEvent(
        session_id=payload.session_id,
        chainage_m=payload.chainage_m,
        defect_class=payload.defect_class,
        severity=payload.severity,
        confidence=payload.confidence,
        stream_source=payload.stream_source,
        image_url=payload.image_url,
        video_timestamp_sec=payload.video_timestamp_sec,
        description=payload.description,
        status=payload.status,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )
    db.add(defect)

    # Increment defect counter on session
    session_obj = db.query(MonitoringSession).filter(MonitoringSession.id == payload.session_id).first()
    if session_obj:
        session_obj.defects_count = (session_obj.defects_count or 0) + 1

    db.commit()
    db.refresh(defect)

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
