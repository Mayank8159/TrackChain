# Liveness/readiness endpoints for orchestration.

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.api.deps import get_db_session

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db_session)):
    """Liveness probe reporting database status and YOLO weights."""
    import src.main as main_mod
    if not main_mod._models_loaded:
        main_mod._load_yolo()

    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    return {
        "status": "ok" if db_ok else "degraded",
        "service": "trackchain-backend",
        "version": "0.1.0",
        "yolo_weights_loaded": bool(main_mod._yolo_loaded),
        "checks": {
            "database": "ok" if db_ok else "error",
            "yolo_weights": "loaded" if main_mod._yolo_loaded else "unavailable",
        },
    }


@router.get("/ready")
def readiness_check(db: Session = Depends(get_db_session)):
    """Readiness probe checking database and dependencies."""
    import src.main as main_mod
    if not main_mod._models_loaded:
        main_mod._load_yolo()

    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    return {
        "status": "ready" if db_ok else "not_ready",
        "yolo_weights_loaded": bool(main_mod._yolo_loaded),
        "checks": {
            "database": "ok" if db_ok else "error",
            "storage": "ok",
            "yolo": "loaded" if main_mod._yolo_loaded else "unavailable",
        },
    }

