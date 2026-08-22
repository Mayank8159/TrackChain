#!/usr/bin/env python3
"""
TrackChain Master Database Seeder.
Supports:
  1. Default mode: Fast, lightweight bootstrap seeding of devices, sessions, and defects.
  2. Realistic mode (--realistic / --physics): 10km high-density EN 13848 physics simulation with IsolationForest.
"""

import os
import sys
import uuid
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np

# Ensure backend root is in sys.path and load environment variables
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv
for env_candidate in [BACKEND_ROOT / ".env", BACKEND_ROOT.parent / ".env", Path(".env")]:
    if env_candidate.exists() and env_candidate.is_file():
        load_dotenv(dotenv_path=env_candidate, override=False)

from src.db.session import SessionLocal, engine, Base
from src.db.models import Device, MonitoringSession, TelemetryRecord, DefectEvent, Alert


def seed_basic(db):
    print("🌱 [SEED] Seeding basic TrackChain reference data...")
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
            last_seen_at=datetime.now(timezone.utc),
        )
        db.add(device)
        db.commit()

    session_id = "ses-delhi-agra-001"
    existing = db.query(MonitoringSession).filter(MonitoringSession.id == session_id).first()
    if existing:
        print("[INFO] Session 'ses-delhi-agra-001' already exists, skipping basic seed.")
        return

    now = datetime.now(timezone.utc)
    session_obj = MonitoringSession(
        id=session_id,
        device_id=device_id,
        name="NDLS-AGC Mainline High-Speed Inspection Run",
        route_name="Northern Railway Corridor 1",
        line_name="Mainline Track 1",
        track_id="IR-NR-01",
        track_section="New Delhi to Mathura Junction (Km 0.0 to 140.0)",
        track_direction="down",
        start_time=now - timedelta(hours=2),
        start_chainage_m=0.0,
        end_chainage_m=140000.0,
        status="running",
        total_distance_km=140.0,
        defects_count=2,
        operator_name="Chief Track Inspector A. Sharma",
        weather="Clear, 28°C",
    )
    db.add(session_obj)
    db.commit()

    telemetry_points = []
    for i in range(200):
        chainage = i * 100.0
        has_anomaly = 40 <= i <= 43
        t_rec = TelemetryRecord(
            id=f"tel-basic-{i:04d}",
            session_id=session_id,
            device_id=device_id,
            timestamp=now - timedelta(seconds=(200 - i) * 2),
            chainage_m=chainage,
            speed_mps=30.5,
            speed_kmh=110.0 + float(np.random.normal(0, 2)),
            vibration_rms=2.6 if has_anomaly else 0.85 + float(np.random.normal(0, 0.1)),
            track_gauge_mm=1690.0 if has_anomaly else 1676.0 + float(np.random.normal(0, 0.5)),
            cant_mm=15.0 + float(np.sin(i / 10.0) * 5),
            twist_mm_per_m=3.8 if has_anomaly else 0.8 + float(np.random.normal(0, 0.2)),
            vertical_unevenness_mm=4.5 if has_anomaly else 1.0,
            alignment_dev_mm=6.2 if has_anomaly else 1.2,
            latitude=28.643 - (i * 0.002),
            longitude=77.219 + (i * 0.001),
        )
        telemetry_points.append(t_rec)

    db.bulk_save_objects(telemetry_points)

    sample_defects = [
        DefectEvent(
            id="def-basic-001",
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
            id="def-basic-002",
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
    print("✅ [OK] Basic database seeding complete.")


def seed_physics(db):
    print("🚂 [SEED] Initializing 10km Real Physics-Driven Track Simulation...")
    try:
        from sklearn.ensemble import IsolationForest
    except ImportError:
        print("[WARN] scikit-learn not available, falling back to basic seed.")
        seed_basic(db)
        return

    device_id = "RPI-ITMS-001"
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        device = Device(
            device_id=device_id,
            device_name="Inspection Bogie Sensor Head (Front)",
            hardware_version="Raspberry Pi 5 + Jetson Orin",
            firmware_version="v2.5.0-prod",
            camera_model="Sony IMX477 4K Global Shutter",
            imu_model="TDK ICM-42688-P",
            gnss_model="u-blox ZED-F9P RTK",
            status="online",
            battery_voltage_v=24.2,
            cpu_temp_c=48.5,
            last_seen_at=datetime.now(timezone.utc),
        )
        db.add(device)
        db.commit()

    session_id = "ses-delhi-agra-001"
    db.query(Alert).filter(Alert.session_id == session_id).delete()
    db.query(DefectEvent).filter(DefectEvent.session_id == session_id).delete()
    db.query(TelemetryRecord).filter(TelemetryRecord.session_id == session_id).delete()
    db.query(MonitoringSession).filter(MonitoringSession.id == session_id).delete()
    db.commit()

    start_time = datetime.now(timezone.utc) - timedelta(hours=2)
    end_time = start_time + timedelta(minutes=15)

    session = MonitoringSession(
        id=session_id,
        device_id=device_id,
        name="NDLS-AGC Mainline Diagnostic Run (10km)",
        route_name="New Delhi - Agra Cantt Corridor",
        line_name="Northern Railway Up-Main",
        track_id="TRACK-MAIN-UP",
        track_section="KM 0.000 - KM 10.000 (NDLS-NZM)",
        track_direction="up",
        start_time=start_time,
        end_time=end_time,
        start_chainage_m=0.0,
        end_chainage_m=10000.0,
        total_distance_km=10.0,
        status="completed",
        defects_count=3,
        operator_name="Chief P-Way Inspector V. Sharma",
        weather="Dry / 28°C / Clear",
    )
    db.add(session)
    db.commit()

    num_points = 10001
    chainages = np.linspace(0.0, 10000.0, num_points)
    lat_start, lon_start = 28.6427, 77.2195
    lat_end, lon_end = 28.5882, 77.2534
    fractions = chainages / 10000.0
    lats = lat_start + fractions * (lat_end - lat_start)
    lons = lon_start + fractions * (lon_end - lon_start)

    speed_kmh = 125.0 + 2.5 * np.sin(chainages / 800.0)
    speed_mps = speed_kmh / 3.6
    gauge_mm = 1676.0 + 0.3 * np.sin(chainages / 15.0) + 0.15 * np.cos(chainages / 4.0)
    cant_mm = np.maximum(0.0, 35.0 * np.sin(chainages / 1200.0))
    vertical_unevenness_mm = 0.25 * np.sin(chainages / 25.0) + 0.1 * np.sin(chainages / 7.0)
    alignment_dev_mm = 0.2 * np.cos(chainages / 30.0)
    vibration_rms = 0.38 + 0.05 * np.abs(np.sin(chainages / 40.0))

    f1_mask = (chainages >= 2495.0) & (chainages <= 2505.0)
    cant_mm[f1_mask] += 15.6 * np.exp(-((chainages[f1_mask] - 2500.0) ** 2) / 12.0)
    vibration_rms[f1_mask] += 0.85

    f2_mask = (chainages >= 4790.0) & (chainages <= 4810.0)
    gauge_mm[f2_mask] += 8.4 * np.exp(-((chainages[f2_mask] - 4800.0) ** 2) / 25.0)
    vibration_rms[f2_mask] += 0.65

    f3_mask = (chainages >= 7190.0) & (chainages <= 7210.0)
    vertical_unevenness_mm[f3_mask] -= 9.2 * np.exp(-((chainages[f3_mask] - 7200.0) ** 2) / 18.0)
    vibration_rms[f3_mask] += 1.45

    # Twist computation
    twist_mm_per_m = np.zeros_like(cant_mm)
    for i in range(len(cant_mm)):
        idx_prev = max(0, i - 3)
        twist_mm_per_m[i] = abs(cant_mm[i] - cant_mm[idx_prev]) / 3.0

    feature_matrix = np.column_stack([
        gauge_mm, cant_mm, twist_mm_per_m, vertical_unevenness_mm, vibration_rms
    ])

    nominal_mask = ~(f1_mask | f2_mask | f3_mask)
    iso_forest = IsolationForest(n_estimators=50, contamination=0.01, random_state=42)
    iso_forest.fit(feature_matrix[nominal_mask])

    raw_scores = -iso_forest.decision_function(feature_matrix)
    norm_scores = (raw_scores - raw_scores.min()) / (raw_scores.max() - raw_scores.min() + 1e-6)

    telemetry_objs = []
    base_time = start_time
    for i in range(num_points):
        t_offset = timedelta(seconds=float(chainages[i] / (speed_mps[i] + 1e-4)))
        rec = TelemetryRecord(
            id=f"tel-phys-{uuid.uuid4().hex[:10]}",
            session_id=session_id,
            device_id=device_id,
            timestamp=base_time + t_offset,
            chainage_m=round(float(chainages[i]), 2),
            latitude=round(float(lats[i]), 6),
            longitude=round(float(lons[i]), 6),
            speed_mps=round(float(speed_mps[i]), 2),
            speed_kmh=round(float(speed_kmh[i]), 1),
            vertical_rms=round(float(vibration_rms[i] * 0.7), 3),
            lateral_rms=round(float(vibration_rms[i] * 0.5), 3),
            longitudinal_rms=round(float(vibration_rms[i] * 0.2), 3),
            vibration_rms=round(float(vibration_rms[i]), 3),
            vibration_index=round(float(norm_scores[i] * 100.0), 1),
            track_gauge_mm=round(float(gauge_mm[i]), 2),
            cant_mm=round(float(cant_mm[i]), 2),
            twist_mm_per_m=round(float(twist_mm_per_m[i]), 2),
            vertical_unevenness_mm=round(float(vertical_unevenness_mm[i]), 2),
            alignment_dev_mm=round(float(alignment_dev_mm[i]), 2),
        )
        telemetry_objs.append(rec)

    db.bulk_save_objects(telemetry_objs)
    db.commit()

    defects_data = [
        {
            "id": "def-twist-2500",
            "chainage_m": 2500.0,
            "lat": float(lats[2500]),
            "lon": float(lons[2500]),
            "defect_class": "track_twist",
            "severity": "critical",
            "confidence": round(float(norm_scores[2500] * 0.3 + 0.68), 4),
            "description": "Critical Track Twist 5.2 mm/m exceeds RDSO Immediate Action Limit (IAL 3.5 mm/m). Mandatory TSR 30 km/h.",
        },
        {
            "id": "def-gauge-4800",
            "chainage_m": 4800.0,
            "lat": float(lats[4800]),
            "lon": float(lons[4800]),
            "defect_class": "gauge_widening",
            "severity": "high",
            "confidence": round(float(norm_scores[4800] * 0.3 + 0.65), 4),
            "description": "Gauge Widening (+8.4 mm, Measured: 1684.4 mm) exceeds RDSO Alert Limit (+6.0 mm). Schedule tamping within 72h.",
        },
        {
            "id": "def-dip-7200",
            "chainage_m": 7200.0,
            "lat": float(lats[7200]),
            "lon": float(lons[7200]),
            "defect_class": "severe_unevenness",
            "severity": "high",
            "confidence": round(float(norm_scores[7200] * 0.3 + 0.62), 4),
            "description": "Localized Vertical Dip (-9.2 mm) generating 1.85g bogie acceleration spike. Inspect ballast bed compaction.",
        },
    ]

    for d in defects_data:
        defect = DefectEvent(
            id=d["id"],
            session_id=session_id,
            device_id=device_id,
            chainage_m=d["chainage_m"],
            latitude=d["lat"],
            longitude=d["lon"],
            defect_class=d["defect_class"],
            severity=d["severity"],
            confidence=d["confidence"],
            source_model="EN 13848-1 Physics + IsolationForest",
            model_version="v2.5.0",
            stream_source="fused",
            status="open",
            image_url="/evidence/track_flaw_sample.jpg",
            video_timestamp_sec=float(d["chainage_m"] / 34.7),
            description=d["description"],
            notes=d["description"],
            created_at=start_time + timedelta(seconds=float(d["chainage_m"] / 34.7)),
        )
        db.add(defect)
        alert = Alert(
            id=f"alt-{d['id']}",
            session_id=session_id,
            defect_id=d["id"],
            severity=d["severity"],
            message=d["description"][:250],
            acknowledged=False,
            created_at=start_time + timedelta(seconds=float(d["chainage_m"] / 34.7)),
        )
        db.add(alert)
    db.commit()
    print("✅ [OK] 10km Physics track session successfully seeded!")


def main():
    parser = argparse.ArgumentParser(description="TrackChain Database Seeder")
    parser.add_argument("--realistic", "--physics", action="store_true", help="Seed 10km high-density physics session")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if args.realistic:
            seed_physics(db)
        else:
            seed_basic(db)
    except Exception as e:
        db.rollback()
        print(f"❌ [ERROR] Seeding failed: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
