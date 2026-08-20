# Dashboard summary route computing high-level track statistics (tc.v1).

from collections import Counter
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.api.deps import get_db_session
from src.db.models import DefectEvent, MonitoringSession, Alert, TelemetryRecord
from src.schemas.dashboard import DashboardSummaryResponse

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(db: Session = Depends(get_db_session)):
    """Fetch high-level KPI metrics for the SCADA dashboard."""
    defects = db.query(DefectEvent).all()
    sessions = db.query(MonitoringSession).all()
    alerts = db.query(Alert).filter(Alert.acknowledged == False).count()

    total_defects = len(defects)
    critical_defects = sum(1 for d in defects if d.severity == "critical")
    distance_covered = sum(s.total_distance_km or 0.0 for s in sessions)

    class_counts = Counter(d.defect_class for d in defects)
    severity_counts = Counter(d.severity for d in defects)

    for sev in ["critical", "high", "medium", "low", "normal"]:
        if sev not in severity_counts:
            severity_counts[sev] = 0

    return DashboardSummaryResponse(
        total_defects=total_defects,
        critical_defects=critical_defects,
        distance_covered_km=round(distance_covered, 2),
        avg_speed_kmh=105.4,
        open_alerts=alerts,
        defect_counts_by_class=dict(class_counts),
        severity_distribution=dict(severity_counts),
    )
