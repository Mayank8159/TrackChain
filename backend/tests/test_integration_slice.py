# Phase 1 & Phase 3 Walking Skeleton: End-to-end vertical integration slice test.

import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.db.session import Base, engine


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


def test_walking_skeleton_vertical_slice():
    client = TestClient(app)

    # 1. Health Probe
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    # 2. Register Device
    device_payload = {
        "device_id": "RPI-ITMS-TEST01",
        "device_name": "Integration Test Unit",
        "hardware_version": "Raspberry Pi 5",
        "firmware_version": "v0.1.0",
    }
    res = client.post("/api/v1/devices", json=device_payload)
    assert res.status_code == 200
    assert res.json()["device_id"] == "RPI-ITMS-TEST01"

    # 3. Start Inspection Session (Testing /api/v1/sessions/start alias)
    session_payload = {
        "name": "Integration Slice Run",
        "track_id": "IR-NR-01",
        "track_section": "Delhi-Agra Test Section",
        "device_id": "RPI-ITMS-TEST01",
        "start_chainage_m": 0.0,
    }
    res = client.post("/api/v1/sessions/start", json=session_payload)
    assert res.status_code == 200
    session_data = res.json()
    session_id = session_data["id"]
    assert session_data["status"] == "running"

    # 4. Ingest Telemetry Batch (Testing /api/v1/telemetry/batch alias)
    telemetry_payload = {
        "schema_version": "tc.v1",
        "idempotency_key": "test-idemp-tel-001",
        "session_id": session_id,
        "device_id": "RPI-ITMS-TEST01",
        "samples": [
            {
                "chainage_m": 12450.0,
                "speed_mps": 30.0,
                "speed_kmh": 108.0,
                "vibration_rms": 2.75,
                "track_gauge_mm": 1448.0,
                "cant_mm": 15.0,
                "twist_mm_per_m": 3.8,
            }
        ],
    }
    res = client.post("/api/v1/telemetry/batch", json=telemetry_payload)
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert res.json()["inserted"] == 1

    # 5. Ingest Fused Defect Batch (Testing /api/v1/defects/batch alias)
    defect_payload = {
        "session_id": session_id,
        "device_id": "RPI-ITMS-TEST01",
        "chainage_m": 12450.0,
        "defect_class": "missing_fastener",
        "defect_family": "visual_component",
        "severity": "critical",
        "decision": "INSPECT_KNOWN",
        "confidence": 0.94,
        "source_model": "yolo_v8_detector",
        "stream_source": "vision",
        "description": "Integration test missing clip detected",
        "latitude": 28.535,
        "longitude": 77.284,
    }
    res = client.post("/api/v1/defects/batch", json=[defect_payload])
    assert res.status_code == 200
    defect_batch_res = res.json()
    assert defect_batch_res["status"] == "ok"
    assert defect_batch_res["inserted"] == 1
    defect_id = defect_batch_res["defect_ids"][0]

    # 6. Retrieve Defect by Session
    res = client.get(f"/api/v1/defects?session_id={session_id}")
    assert res.status_code == 200
    defects = res.json()
    assert len(defects) >= 1
    found = any(d["id"] == defect_id for d in defects)
    assert found is True

    # 7. Retrieve Telemetry with Downsampling (Testing /api/v1/telemetry/{session_id})
    res_tel = client.get(f"/api/v1/telemetry/{session_id}?downsample=500")
    assert res_tel.status_code == 200
    tel_points = res_tel.json()
    assert len(tel_points) >= 1

    # 8. Verify Dashboard KPI Summary
    res = client.get("/api/v1/dashboard/summary")
    assert res.status_code == 200
    summary = res.json()
    assert summary["total_defects"] >= 1
    assert summary["critical_defects"] >= 1
