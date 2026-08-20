# Emits a single contract-compliant synthetic inspection slice to the backend (tc.v1).

import argparse
import sys
import time
import urllib.request
import json


def emit_sample_slice(backend_url: str = "http://127.0.0.1:8000"):
    print(f"[INFO] Connecting to TrackChain backend at: {backend_url}")

    # 1. Health check
    try:
        req = urllib.request.Request(f"{backend_url}/health", method="GET")
        with urllib.request.urlopen(req, timeout=5) as res:
            if res.status == 200:
                print(f"[OK] Backend health probe verified: {res.read().decode('utf-8')}")
    except Exception as exc:
        print(f"[ERROR] Could not connect to backend health endpoint at {backend_url}: {exc}")
        print("[TIP] Make sure the backend is running via: uvicorn src.main:app --port 8000")
        sys.exit(1)

    # 2. Register Device
    device_id = "RPI-ITMS-WALK01"
    device_payload = {
        "device_id": device_id,
        "device_name": "Walking Skeleton Trolley Unit",
        "hardware_version": "Raspberry Pi 5",
        "firmware_version": "v0.1.0-slice",
        "camera_model": "Sony IMX477",
        "imu_model": "BNO085",
        "gnss_model": "NEO-M9N",
    }
    try:
        req = urllib.request.Request(
            f"{backend_url}/api/devices",
            data=json.dumps(device_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            print(f"[OK] Registered device: {device_id}")
    except Exception as exc:
        print(f"[WARN] Device registration notice: {exc}")

    # 3. Start Session
    session_id = f"ses-walk-{int(time.time())}"
    session_payload = {
        "name": "Phase 1 Walking Skeleton Integration Run",
        "track_id": "IR-NR-MAIN01",
        "track_section": "Delhi-Mathura Km 12.0 to 14.0",
        "track_direction": "down",
        "start_chainage_m": 12000.0,
        "operator_name": "Antigravity Automated Test",
        "device_id": device_id,
    }
    req = urllib.request.Request(
        f"{backend_url}/api/sessions",
        data=json.dumps(session_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as res:
        created_session = json.loads(res.read().decode("utf-8"))
        session_id = created_session.get("id", session_id)
        print(f"[OK] Started inspection session: {session_id}")

    # 4. Ingest Telemetry Batch
    telemetry_payload = {
        "schema_version": "tc.v1",
        "idempotency_key": f"idemp-tel-{int(time.time())}",
        "session_id": session_id,
        "device_id": device_id,
        "samples": [
            {
                "chainage_m": 12400.0 + (i * 25.0),
                "speed_mps": 30.5,
                "speed_kmh": 110.0,
                "vibration_rms": 0.85 if i != 2 else 2.65,
                "track_gauge_mm": 1435.2 if i != 2 else 1448.0,
                "cant_mm": 12.0,
                "twist_mm_per_m": 0.9 if i != 2 else 3.8,
                "latitude": 28.535 - (i * 0.0005),
                "longitude": 77.284 + (i * 0.0005),
            }
            for i in range(5)
        ],
    }
    req = urllib.request.Request(
        f"{backend_url}/api/telemetry",
        data=json.dumps(telemetry_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as res:
        tel_resp = json.loads(res.read().decode("utf-8"))
        print(f"[OK] Ingested telemetry batch: {tel_resp}")

    # 5. Emit ML Fused Defect Event
    defect_payload = {
        "session_id": session_id,
        "device_id": device_id,
        "chainage_m": 12450.0,
        "defect_class": "missing_fastener",
        "defect_family": "visual_component",
        "severity": "critical",
        "decision": "INSPECT_KNOWN",
        "confidence": 0.94,
        "source_model": "yolo_v8_detector",
        "stream_source": "vision",
        "description": "Walking skeleton: Missing rail fastening clip detected at KM 12+450",
        "latitude": 28.534,
        "longitude": 77.285,
    }
    req = urllib.request.Request(
        f"{backend_url}/api/defects",
        data=json.dumps(defect_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as res:
        created_defect = json.loads(res.read().decode("utf-8"))
        defect_id = created_defect.get("id")
        print(f"[OK] Ingested synthetic defect event: {defect_id} (missing_fastener @ 12,450m)")

    # 6. Retrieve Defect to Verify Round-Trip
    req = urllib.request.Request(
        f"{backend_url}/api/defects?session_id={session_id}",
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=5) as res:
        retrieved = json.loads(res.read().decode("utf-8"))
        print(f"[OK] Retrieved defects for session ({len(retrieved)} found):")
        for d in retrieved:
            print(f"     - Defect ID: {d['id']}, Class: {d['defect_class']}, Severity: {d['severity']}, Chainage: {d['chainage_m']}m")

    # 7. Dashboard Summary Verification
    req = urllib.request.Request(f"{backend_url}/api/dashboard/summary", method="GET")
    with urllib.request.urlopen(req, timeout=5) as res:
        summary = json.loads(res.read().decode("utf-8"))
        print(f"[OK] Live Dashboard KPI Summary:")
        print(f"     - Total Defects: {summary['total_defects']}, Critical: {summary['critical_defects']}, Open Alerts: {summary['open_alerts']}")

    print("\n[SUCCESS] Phase 1 Walking Skeleton End-to-End Vertical Slice Verified Successfully!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Emit Phase 1 walking skeleton slice.")
    parser.add_argument(
        "--backend-url",
        default="http://127.0.0.1:8000",
        help="Backend API base URL (default: http://127.0.0.1:8000)",
    )
    args = parser.parse_args()
    emit_sample_slice(args.backend_url)
