# Session/run management: create, list, and summarize runs (tc.v1).

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from src.api.deps import get_db_session
from src.db.models import MonitoringSession
from src.schemas.sessions import SessionStartRequest, SessionResponse

# Backward compatibility alias
SessionCreate = SessionStartRequest

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])


@router.post("", response_model=SessionResponse)
def create_session(payload: SessionStartRequest, db: Session = Depends(get_db_session)):
    """Create a new track inspection session."""
    ses = MonitoringSession(
        name=payload.name,
        track_id=payload.track_id,
        track_section=payload.track_section,
        track_direction=payload.track_direction,
        operator_name=payload.operator_name,
        weather=payload.weather,
        device_id=payload.device_id,
        status="running",
    )
    db.add(ses)
    db.commit()
    db.refresh(ses)
    return ses


@router.get("", response_model=List[SessionResponse])
def list_sessions(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db_session),
):
    """List inspection runs and summary statistics."""
    return (
        db.query(MonitoringSession)
        .order_by(MonitoringSession.start_time.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/{session_id}", response_model=SessionResponse)
def get_session_by_id(session_id: str, db: Session = Depends(get_db_session)):
    """Retrieve detailed session summary."""
    ses = db.query(MonitoringSession).filter(MonitoringSession.id == session_id).first()
    if not ses:
        raise HTTPException(status_code=404, detail="Session not found")
    return ses
