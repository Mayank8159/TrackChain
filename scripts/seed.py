# Seed the database with sample sessions, telemetry, and defects (tc.v1).

import os
import sys
from datetime import datetime, timedelta
import numpy as np

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath("backend"))

from src.db.session import SessionLocal, engine, Base
from src.db.models import Device, MonitoringSession, TrackSegment, TelemetryRecord, DefectEvent, MediaAsset, MLSignal


def seed_database():
    print("[INFO] Seeding TrackChain database with sample inspection run...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Create edge device
        device_id = "RPI-ITMS-001"
        device = db.query(Device).filter(Device.device_id == device_id).first()
        if not device:
            device = Device(
                device_id=device_id,
                device_name="Inspection Car Alpha (Trolley)",
                hardware_version="Raspberry Pi 5 8GB + Coral TPU",
                firmware_version="v0.1.0",
                camera_model="Sony IMX477 12MP 60fps",
                imu_model="BNO085 9-DoF IMU",
                gnss_model="u-blox NEO-M9N GNSS",
                status="online",
                battery_voltage_v=12.4,
                cpu_temp_c=48.5,
                last_seen_at=datetime.utcnow(),
            )
            db.add(device)
            db.commit()

        # Create active inspection session
        session_id = "ses-delhi-agra-001"
        existing = db.query(MonitoringSession).filter(MonitoringSession.id == session_id).first()
        if existing:
            print("[INFO] Session already exists, skipping.")
            return

        session_obj = MonitoringSession(
            id=session_id,
            device_id=device_id,
            name="NDLS-AGC Mainline High-Speed Inspection Run",
            route_name="Northern Railway Corridor 1",
            line_name="Mainline Track 1",
            track_id="IR-NR-01",
            track_section="New Delhi to Mathura Junction (Km 0.0 to 140.0)",
            track_direction="down",
            start_time=datetime.utcnow() - timedelta(hours=2),
            start_chainage_m=0.0,
            end_chainage_m=140000.0,
            status="running",
            total_distance_km=140.0,
            defects_count=5,
            operator_name="Chief Track Inspector A. Sharma",
            weather="Clear, 28°C",
        )
        db.add(session_obj)
        db.commit()

        # Create sample telemetry records
        telemetry_points = []
        now = datetime.utcnow()
        for i in range(200):
            chainage = i * 100.0  # every 100m
            has_anomaly = 40 <= i <= 43
            t_rec = TelemetryRecord(
                session_id=session_id,
                device_id=device_id,
                timestamp=now - timedelta(seconds=(200 - i) * 2),
                chainage_m=chainage,
                speed_mps=30.5,
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
                device_id=device_id,
                chainage_m=4200.0,
                defect_class="gauge_widening",
                defect_family="geometry",
                severity="critical",
                decision="INSPECT_KNOWN",
                confidence=0.95,
                source_model="en13848_physics_detector",
                stream_source="geometry",
                description="Gauge widened to 1448mm (+13mm above allowable AL limit)",
                status="open",
                latitude=28.559,
                longitude=77.261,
            ),
            DefectEvent(
                session_id=session_id,
                device_id=device_id,
                chainage_m=8600.0,
                defect_class="crack",
                defect_family="visual_surface",
                severity="high",
                decision="INSPECT_KNOWN",
                confidence=0.91,
                source_model="yolo_v8_detector",
                stream_source="vision",
                description="Longitudinal surface crack detected on right rail head",
                status="open",
                latitude=28.471,
                longitude=77.305,
            ),
        ]
        db.bulk_save_objects(sample_defects)
        db.commit()
        print("[OK] Database seeding complete.")
    except Exception as exc:
        db.rollback()
        print(f"[ERROR] Seeding failed: {exc}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
