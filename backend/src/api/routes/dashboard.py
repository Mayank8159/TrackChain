# Dashboard summary and RDSO report batch export route (tc.v1 SOTA).

import csv
import io
from collections import Counter
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
from src.api.deps import get_db_session
from src.db.models import DefectEvent, MonitoringSession, Alert, TelemetryRecord
from src.schemas.dashboard import DashboardSummaryResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


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


@router.get("/export/{session_id}")
def export_session_report(
    session_id: str,
    format: str = Query(default="csv", description="Export format: 'csv' for RDSO spreadsheets or 'parquet' for data lakes"),
    db: Session = Depends(get_db_session),
):
    """Export track inspection session defects and telemetry for official RDSO compliance reporting."""
    defects = db.query(DefectEvent).filter(DefectEvent.session_id == session_id).all()

    if format.lower() == "csv":
        out = io.StringIO()
        fieldnames = [
            "defect_id",
            "session_id",
            "chainage_m",
            "defect_class",
            "severity",
            "confidence",
            "source_model",
            "latitude",
            "longitude",
            "timestamp",
        ]
        writer = csv.DictWriter(out, fieldnames=fieldnames)
        writer.writeheader()

        for d in defects:
            writer.writerow({
                "defect_id": d.id,
                "session_id": d.session_id,
                "chainage_m": d.chainage_m,
                "defect_class": d.defect_class,
                "severity": d.severity,
                "confidence": d.confidence,
                "source_model": d.source_model,
                "latitude": d.latitude or "",
                "longitude": d.longitude or "",
                "timestamp": d.timestamp.isoformat() if d.timestamp else "",
            })

        out.seek(0)
        return StreamingResponse(
            io.BytesIO(out.getvalue().encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="trackchain_session_{session_id}.csv"'},
        )

    elif format.lower() == "parquet":
        import pyarrow as pa
        import pyarrow.parquet as pq

        table = pa.Table.from_arrays(
            [
                pa.array([d.id for d in defects], pa.string()),
                pa.array([d.session_id for d in defects], pa.string()),
                pa.array([float(d.chainage_m) for d in defects], pa.float64()),
                pa.array([d.defect_class for d in defects], pa.string()),
                pa.array([d.severity for d in defects], pa.string()),
                pa.array([float(d.confidence) for d in defects], pa.float64()),
                pa.array([d.source_model for d in defects], pa.string()),
                pa.array([float(d.latitude) if d.latitude is not None else 0.0 for d in defects], pa.float64()),
                pa.array([float(d.longitude) if d.longitude is not None else 0.0 for d in defects], pa.float64()),
            ],
            names=[
                "defect_id",
                "session_id",
                "chainage_m",
                "defect_class",
                "severity",
                "confidence",
                "source_model",
                "latitude",
                "longitude",
            ],
        )

        buf = io.BytesIO()
        pq.write_table(table, buf)
        buf.seek(0)

        return StreamingResponse(
            buf,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="trackchain_session_{session_id}.parquet"'},
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported export format: {format}")
