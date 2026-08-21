# Emits a full SOTA contract-compliant inspection slice to the backend (tc.v1).
# Supports Device Registration, JWT Token Exchange, HMAC-SHA256 Request Signing, Telemetry, and ML Fusion Defect Ingestion.

import argparse
import hashlib
import hmac
import json
import sys
import time
import urllib.request
from typing import Dict, Any


def sign_request(secret: str, payload_bytes: bytes, timestamp_str: str) -> str:
    """Compute HMAC-SHA256 signature for body + timestamp."""
    msg = payload_bytes + timestamp_str.encode("utf-8")
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def emit_sample_slice(
    backend_url: str = "http://127.0.0.1:8000",
    signing_secret: str = "trackchain-request-signing-secret-change-in-production",
):
    print(f"[INFO] Connecting to TrackChain backend at: {backend_url}")

    # 1. Health check & Observability Probing
    try:
        req = urllib.request.Request(f"{backend_url}/health", method="GET")
        with urllib.request.urlopen(req, timeout=5) as res:
            if res.status == 200:
                print(f"[OK] Backend health probe verified: {res.read().decode('utf-8')}")
    except Exception as exc:
        print(f"[ERROR] Could not connect to backend health endpoint at {backend_url}: {exc}")
        print("[TIP] Make sure the backend is running via: uvicorn src.main:app --port 8000")
        sys.exit(1)

    # 2. Register Edge Inspection Device
    device_id = f"RPI-5-ITMS-{int(time.time()) % 10000:04d}"
    device_payload = {
        "device_id": device_id,
        "name": "Track Inspection Cart Unit 1",
        "hardware_version": "Raspberry Pi 5 (8GB)",
        "firmware_version": "v1.4.2-prod",
        "camera_model": "Sony IMX477 1080p60",
        "imu_model": "Bosch BNO085 100Hz",
        "gnss_model": "u-blox NEO-M9N RTK",
    }
    raw_api_key = None
    try:
        data = json.dumps(device_payload).encode("utf-8")
        req = urllib.request.Request(
            f"{backend_url}/api/v1/devices/register",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            reg_resp = json.loads(res.read().decode("utf-8"))
            raw_api_key = reg_resp.get("api_key")
            print(f"[OK] Registered edge device: {device_id} (API Key: {raw_api_key[:12]}...)")
    except Exception as exc:
        print(f"[ERROR] Device registration failed: {exc}")
        sys.exit(1)

    # 3. Exchange API Key for Scoped JWT Token
    access_token = None
    try:
        token_payload = {"device_id": device_id, "api_key": raw_api_key}
        data = json.dumps(token_payload).encode("utf-8")
        req = urllib.request.Request(
            f"{backend_url}/api/v1/devices/token",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            token_resp = json.loads(res.read().decode("utf-8"))
            access_token = token_resp.get("access_token")
            print(f"[OK] Authenticated JWT access token issued: {access_token[:18]}... (Expires: {token_resp.get('expires_in_seconds')}s)")
    except Exception as exc:
        print(f"[ERROR] Token exchange failed: {exc}")
        sys.exit(1)

    auth_headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
    }

    # 4. Start Monitoring Session
    session_id = f"ses-live-{int(time.time())}"
    session_payload = {
        "id": session_id,
        "name": "Northern Railway Track Maintenance Inspection",
        "track_id": "IR-NR-MAIN01",
        "track_section": "Delhi-Mathura Km 102.0 to 108.0",
        "track_direction": "down",
        "start_chainage_m": 102000.0,
        "operator_name": "Senior Section Engineer (P-Way)",
        "device_id": device_id,
    }
    try:
        data = json.dumps(session_payload).encode("utf-8")
        req = urllib.request.Request(
            f"{backend_url}/api/v1/sessions",
            data=data,
            headers=auth_headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            created_session = json.loads(res.read().decode("utf-8"))
            session_id = created_session.get("id", session_id)
            print(f"[OK] Started monitoring session: {session_id} on {session_payload['track_section']}")
    except Exception as exc:
        print(f"[ERROR] Session creation failed: {exc}")
        sys.exit(1)

    # 5. Ingest High-Frequency Telemetry Batch with HMAC Signing
    telemetry_payload = {
        "schema_version": "tc.v1",
        "idempotency_key": f"idemp-tel-{int(time.time())}",
        "session_id": session_id,
        "device_id": device_id,
        "samples": [
            {
                "chainage_m": 102400.0 + (i * 25.0),
                "speed_mps": 30.5,
                "speed_kmh": 109.8,
                "vibration_rms": 0.85 if i != 2 else 3.25,
                "track_gauge_mm": 1676.0 if i != 2 else 1692.5,
                "cant_mm": 12.0,
                "twist_mm_per_m": 0.8 if i != 2 else 4.6,
                "latitude": 28.535 - (i * 0.0005),
                "longitude": 77.284 + (i * 0.0005),
            }
            for i in range(10)
        ],
    }
    ts_str = str(int(time.time()))
    tel_bytes = json.dumps(telemetry_payload).encode("utf-8")
    sig = sign_request(signing_secret, tel_bytes, ts_str)

    tel_headers = auth_headers.copy()
    tel_headers["X-Signature"] = sig
    tel_headers["X-Timestamp"] = ts_str
    tel_headers["X-Idempotency-Key"] = telemetry_payload["idempotency_key"]

    try:
        req = urllib.request.Request(
            f"{backend_url}/api/v1/telemetry/batch",
            data=tel_bytes,
            headers=tel_headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as res:
            tel_resp = json.loads(res.read().decode("utf-8"))
            print(f"[OK] Ingested HMAC-signed telemetry batch: {tel_resp['inserted']} samples (session: {tel_resp['session_id']})")
    except Exception as exc:
        print(f"[ERROR] Telemetry ingestion failed: {exc}")
        sys.exit(1)

    # 6. Ingest Multi-Modal ML Fused Defect Event with Explainability
    defect_payload = {
        "session_id": session_id,
        "device_id": device_id,
        "chainage_m": 102450.0,
        "defect_class": "missing_fastener",
        "defect_family": "visual_component",
        "severity": "critical",
        "decision": "INSPECT_KNOWN",
        "confidence": 0.94,
        "source_model": "yolo_v8_detector",
        "stream_source": "vision",
        "description": "Multi-modal confirmation: Missing fastening clip with coincident lateral acceleration spike at KM 102+450",
        "latitude": 28.534,
        "longitude": 77.285,
        "supporting_signals": [
            {
                "model_name": "yolo_v8_detector",
                "model_version": "v1.0.0",
                "signal_type": "bounding_box",
                "raw_score": 0.94,
                "calibrated_score": 0.94,
                "threshold": 0.5,
                "fired": True,
                "label": "missing_fastener",
                "bbox": [120.0, 240.0, 180.0, 310.0],
                "explanation": "High-confidence visual missing fastener detection",
            },
            {
                "model_name": "en13848_physics_engine",
                "model_version": "v1.0.0",
                "signal_type": "exceedance",
                "raw_score": 4.6,
                "calibrated_score": 0.82,
                "threshold": 0.5,
                "fired": True,
                "label": "twist_fault",
                "explanation": "Twist exceeds EN 13848 safety limit (4.6mm/m > 4.0mm/m)",
            },
        ],
    }
    defect_bytes = json.dumps(defect_payload).encode("utf-8")
    req = urllib.request.Request(
        f"{backend_url}/api/v1/defects",
        data=defect_bytes,
        headers=auth_headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            created_defect = json.loads(res.read().decode("utf-8"))
            defect_id = created_defect.get("id")
            print(f"[OK] Ingested fused defect event: {defect_id}")
            print(f"     - Class: {created_defect['defect_class']}, Severity: {created_defect['severity']}, Confidence: {created_defect['confidence']}")
            print(f"     - Supporting Signals: {len(created_defect.get('supporting_signals', []))} ML models linked for explainability")
    except Exception as exc:
        print(f"[ERROR] Defect event ingestion failed: {exc}")
        sys.exit(1)

    # 7. Dashboard KPI Verification
    try:
        req = urllib.request.Request(f"{backend_url}/api/v1/dashboard/summary", headers=auth_headers, method="GET")
        with urllib.request.urlopen(req, timeout=5) as res:
            summary = json.loads(res.read().decode("utf-8"))
            print(f"[OK] Live Dashboard KPI Summary:")
            print(f"     - Total Defects: {summary['total_defects']}, Critical: {summary['critical_defects']}, Open Alerts: {summary['open_alerts']}")
    except Exception as exc:
        print(f"[ERROR] Dashboard summary query failed: {exc}")

    # 8. Prometheus Metrics Verification
    try:
        req = urllib.request.Request(f"{backend_url}/metrics", method="GET")
        with urllib.request.urlopen(req, timeout=5) as res:
            metrics_raw = res.read().decode("utf-8")
            has_req = "trackchain_http_requests_total" in metrics_raw
            has_def = "trackchain_defects_created_total" in metrics_raw
            print(f"[OK] Prometheus Observability: HTTP Metrics: {has_req}, Defect Metrics: {has_def}")
    except Exception as exc:
        print(f"[WARN] Metrics query notice: {exc}")

    print("\n" + "=" * 80)
    print(" [SUCCESS] TrackChain Edge-to-Cloud Integration Slice Verified Successfully!")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Emit TrackChain SOTA production inspection slice.")
    parser.add_argument(
        "--backend-url",
        default="http://127.0.0.1:8000",
        help="Backend API base URL (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--signing-secret",
        default="trackchain-request-signing-secret-change-in-production",
        help="HMAC-SHA256 request signing secret",
    )
    args = parser.parse_args()
    emit_sample_slice(args.backend_url, args.signing_secret)
