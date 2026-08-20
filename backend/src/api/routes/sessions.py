# Session/run management: create, list, and summarize runs.

from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from src.api.deps import get_db_session
from src.db.models import MonitoringSession

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])


class SessionCreate(BaseModel):
    name: str
    track_id: str
    track_section: str
    operator_name: Optional[str] = None


class SessionResponse(SessionCreate):
    id: str
    status: str
    total_distance_km: float
    defects_count: int

    class Config:
        from_attributes = True


@router.post("", response_model=SessionResponse)
def create_session(payload: SessionCreate, db: Session = Depends(get_db_session)):
    """Create a new track inspection session."""
    ses = MonitoringSession(
        name=payload.name,
        track_id=payload.track_id,
        track_section=payload.track_section,
        operator_name=payload.operator_name,
        status="active",
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
