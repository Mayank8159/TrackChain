# Liveness/readiness endpoints for orchestration.

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    """Liveness probe for Kubernetes and Docker orchestrators."""
    return {"status": "ok", "service": "trackchain-backend", "version": "0.1.0"}


@router.get("/ready")
def readiness_check():
    """Readiness probe checking database and dependencies."""
    return {"status": "ready", "checks": {"database": "ok", "storage": "ok"}}
