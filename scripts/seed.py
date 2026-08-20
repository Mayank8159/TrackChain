# Seed the database with sample sessions, telemetry, and defects.

import os
import sys
from datetime import datetime, timedelta
import numpy as np

# Add backend/src to path
sys.path.insert(0, os.path.abspath("backend/src"))

from src.db.session import SessionLocal, engine, Base
from src.db.models import MonitoringSession, TelemetryRecord, DefectEvent


def seed_database():
    print("🌱 Seeding TrackChain database with sample inspection run...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Create active inspection session
        session_id = "ses-delhi-agra-001"
        existing = db.query(MonitoringSession).filter(MonitoringSession.id == session_id).first()
        if existing:
            print("Session already exists, skipping.")
            return

        session_obj = MonitoringSession(
            id=session_id,
            name="NDLS-AGC Mainline High-Speed Inspection Run",
            track_id="IR-NR-01",
            track_section="New Delhi to Mathura Junction (Km 0.0 to 140.0)",
            start_time=datetime.utcnow() - timedelta(hours=2),
            status="active",
            total_distance_km=140.0,
            defects_count=5,
            operator_name="Chief Track Inspector A. Sharma",
        )
        db.add(session_obj)

        # Create sample telemetry records
        telemetry_points = []
        now = datetime.utcnow()
        for i in range(200):
            chainage = i * 100.0  # every 100m
            has_anomaly = 40 <= i <= 43
            t_rec = TelemetryRecord(
                session_id=session_id,
                timestamp=now - timedelta(seconds=(200 - i) * 2),
                chainage_m=chainage,
                speed_kmh=110.0 + float(np.random.normal(0, 2)),
                vibration_rms=2.6 if has_anomaly else 0.85 + float(np.random.normal(0, 0.1)),
                track_gauge_mm=1448.0 if has_anomaly else 1435.0 + float(np.random.normal(0, 0.5)),
                cant_mm=15.0 + float(np.sin(i / 10.0) * 5),
                twist_mm_per_m=3.8 if has_anomaly else 0.8 + float(np.random.normal(0, 0.2)),
                vertical_unevenness_mm=4.5 if has_anomaly else 1.0,
                alignment_dev_mm=6.2 if has_anomaly else 1.2,
                latitude=28.643 - (i * 0.002),
                longitude=77.219 + (i * 0.001),
            )
            telemetry_points.append(t_rec)

        db.bulk_save_objects(telemetry_points)

        # Create sample defect events
        sample_defects = [
            DefectEvent(
                session_id=session_id,
                chainage_m=4200.0,
                defect_class="gauge_widening",
                severity="critical",
                confidence=0.95,
                stream_source="geometry",
                description="Gauge widened to 1448mm (+13mm above allowable AL limit)",
                status="open",
                latitude=28.559,
                longitude=77.261,
            ),
            DefectEvent(
                session_id=session_id,
                chainage_m=8600.0,
                defect_class="crack",
                severity="high",
                confidence=0.91,
                stream_source="vision",
                description="Longitudinal surface crack detected on right rail head",
                status="open",
                latitude=28.471,
                longitude=77.305,
            ),
        ]
        db.bulk_save_objects(sample_defects)
        db.commit()
        print("✅ Database seeding complete.")
    except Exception as exc:
        db.rollback()
        print(f"❌ Seeding failed: {exc}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
