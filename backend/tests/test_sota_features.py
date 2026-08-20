# Comprehensive test suite for Phase 1 SOTA Foundation Features (tc.v1).

import time
import asyncio
import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.db.session import Base, engine
from src.services.alerts import register_subscriber, broadcast_event, unregister_subscriber


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


def test_sota_feature_1_idempotent_ingestion():
    client = TestClient(app)
    idemp_key = f"idemp-test-{int(time.time())}"

    payload = {
        "schema_version": "tc.v1",
        "idempotency_key": idemp_key,
        "session_id": "ses-idemp-001",
        "device_id": "RPI-TEST-01",
        "samples": [
            {
                "chainage_m": 1000.0,
                "speed_mps": 25.0,
                "speed_kmh": 90.0,
                "vibration_rms": 0.5,
                "track_gauge_mm": 1435.0,
                "cant_mm": 0.0,
                "twist_mm_per_m": 0.1,
            }
        ],
    }

    # First request -> inserts
    res1 = client.post("/api/telemetry", json=payload, headers={"X-Idempotency-Key": idemp_key})
    assert res1.status_code == 200
    assert res1.json()["status"] == "ok"
    assert res1.json()["inserted"] == 1

    # Second request with SAME key -> returns cached idempotent response
    res2 = client.post("/api/telemetry", json=payload, headers={"X-Idempotency-Key": idemp_key})
    assert res2.status_code == 200
    assert res2.json()["status"] == "ok"
    assert res2.json()["inserted"] == 1


def test_sota_feature_2_ml_signals_explainability():
    client = TestClient(app)

    # 1. Create a session
    sess_res = client.post("/api/sessions", json={
        "name": "Explainability Run",
        "track_id": "IR-EXP-01",
        "track_section": "Km 50 to 55",
    })
    session_id = sess_res.json()["id"]

    # 2. Ingest defect with supporting ML signals (YOLO + PatchCore)
    defect_payload = {
        "session_id": session_id,
        "chainage_m": 50250.0,
        "defect_class": "crack",
        "defect_family": "visual_surface",
        "severity": "critical",
        "decision": "INSPECT_KNOWN",
        "confidence": 0.96,
        "source_model": "yolo_v8_detector",
        "stream_source": "fused",
        "description": "Rail surface crack flagged by vision detector and anomaly model",
        "supporting_signals": [
            {
                "session_id": session_id,
                "model_name": "yolo_v8_surface_detector",
                "model_version": "v1.2.0",
                "signal_type": "visual_known",
                "raw_score": 0.96,
                "calibrated_score": 0.95,
                "threshold": 0.80,
                "fired": True,
                "label": "crack",
                "bbox": [100.0, 150.0, 220.0, 310.0],
                "explanation": "High-confidence bounding box match on head crack",
            },
            {
                "session_id": session_id,
                "model_name": "patchcore_visual_anomaly",
                "model_version": "v1.0.0",
                "signal_type": "visual_novel",
                "raw_score": 0.88,
                "calibrated_score": 0.87,
                "threshold": 0.75,
                "fired": True,
                "explanation": "Texture distance exceedance in visual patch embedding",
            },
        ],
    }

    res = client.post("/api/defects", json=defect_payload)
    assert res.status_code == 200
    defect = res.json()
    defect_id = defect["id"]

    # 3. Retrieve defect by ID and verify supporting signals are attached
    get_res = client.get(f"/api/defects/{defect_id}")
    assert get_res.status_code == 200
    retrieved = get_res.json()
    assert len(retrieved["supporting_signals"]) == 2
    assert retrieved["supporting_signals"][0]["model_name"] == "yolo_v8_surface_detector"
    assert retrieved["supporting_signals"][1]["signal_type"] == "visual_novel"


def test_sota_feature_3_media_asset_contract():
    client = TestClient(app)

    # 1. Presign Upload URL
    presign_req = {
        "session_id": "ses-media-001",
        "media_type": "evidence_image",
        "filename": "defect_frame_km12450.jpg",
        "content_type": "image/jpeg",
        "chainage_start_m": 12450.0,
    }
    res = client.post("/api/media/presign-upload", json=presign_req)
    assert res.status_code == 200
    media_data = res.json()
    assert "upload_url" in media_data
    media_id = media_data["media_id"]

    # 2. Complete Upload
    complete_req = {
        "media_id": media_id,
        "upload_status": "uploaded",
        "size_bytes": 1048576,
        "checksum": "sha256:abc123mock",
    }
    res2 = client.post("/api/media/complete", json=complete_req)
    assert res2.status_code == 200
    assert res2.json()["upload_status"] == "uploaded"

    # 3. Presign Download URL
    res3 = client.get(f"/api/media/{media_id}/presign-download")
    assert res3.status_code == 200
    assert "download_url" in res3.json()


def test_sota_feature_4_telemetry_lttb_downsampling():
    client = TestClient(app)
    session_id = f"ses-downsample-{int(time.time())}"

    # Ingest 25 telemetry points with a severe twist spike at index 12
    samples = []
    for i in range(25):
        samples.append({
            "chainage_m": float(i * 10),
            "speed_mps": 20.0,
            "speed_kmh": 72.0,
            "vibration_rms": 5.5 if i == 12 else 0.8,
            "track_gauge_mm": 1435.0,
            "cant_mm": 0.0,
            "twist_mm_per_m": 8.0 if i == 12 else 0.5,
        })

    client.post("/api/telemetry", json={
        "schema_version": "tc.v1",
        "idempotency_key": f"idemp-{session_id}",
        "session_id": session_id,
        "device_id": "RPI-01",
        "samples": samples,
    })

    # Query with downsample=6
    res = client.get(f"/api/telemetry?session_id={session_id}&downsample=6")
    assert res.status_code == 200
    points = res.json()
    assert len(points) == 6
    # Verify first and last point are retained
    assert points[0]["chainage_m"] == 0.0
    assert points[-1]["chainage_m"] == 240.0


def test_sota_feature_5_sse_alerts_stream_and_broker():
    # 1. Test Broker Registration & Event Broadcast
    q = register_subscriber()
    assert q is not None

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(broadcast_event("defect_alert", {"defect_class": "crack", "severity": "critical"}))

    msg = q.get_nowait()
    assert msg["event"] == "defect_alert"
    assert msg["data"]["defect_class"] == "crack"
    assert msg["data"]["severity"] == "critical"

    unregister_subscriber(q)
