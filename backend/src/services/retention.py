# Data lifecycle and retention policy service (tc.v1 SOTA).

from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from sqlalchemy.orm import Session
from src.db.session import SessionLocal
from src.db.models import TelemetryRecord, MediaAsset, MLSignal


def apply_retention_policies(
    db: Session,
    telemetry_retention_days: int = 90,
    media_retention_days: int = 180,
    signals_retention_days: int = 90,
) -> Dict[str, Any]:
    """
    Automated data lifecycle management.
    Deletes raw high-frequency telemetry samples older than 90 days and media older than 180 days.
    DefectEvents and session summaries are preserved permanently for compliance.
    """
    now = datetime.now(timezone.utc)

    # 1. Telemetry retention
    tel_cutoff = now - timedelta(days=telemetry_retention_days)
    deleted_telemetry = (
        db.query(TelemetryRecord)
        .filter(TelemetryRecord.timestamp < tel_cutoff)
        .delete(synchronize_session=False)
    )

    # 2. Raw ML signals retention
    sig_cutoff = now - timedelta(days=signals_retention_days)
    deleted_signals = (
        db.query(MLSignal)
        .filter(MLSignal.timestamp < sig_cutoff)
        .delete(synchronize_session=False)
    )

    # 3. Media assets retention
    media_cutoff = now - timedelta(days=media_retention_days)
    deleted_media = (
        db.query(MediaAsset)
        .filter(MediaAsset.created_at < media_cutoff)
        .delete(synchronize_session=False)
    )

    db.commit()

    return {
        "status": "completed",
        "deleted_telemetry_samples": deleted_telemetry,
        "deleted_ml_signals": deleted_signals,
        "deleted_media_assets": deleted_media,
        "executed_at": now.isoformat(),
    }


def lambda_handler(event, context):
    """AWS Lambda scheduled entrypoint for CloudWatch Events cron."""
    db = SessionLocal()
    try:
        res = apply_retention_policies(db)
        return {"statusCode": 200, "body": res}
    finally:
        db.close()
