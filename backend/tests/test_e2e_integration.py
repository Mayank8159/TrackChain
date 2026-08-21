# End-to-end integration test suite verifying full stack: Auth -> Video -> ML Pipeline -> Alerts -> Dashboard (tc.v1 SOTA).

import time
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from src.main import app
from src.db.session import Base, engine, SessionLocal
from src.db.models import Device, MonitoringSession, MediaAsset, DefectEvent


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield


def test_e2e_device_auth_lifecycle():
    client = TestClient(app)

    # 1. Register new edge inspection unit
    reg_payload = {
        "device_id": "RPI-E2E-001",
        "device_name": "Northern Railway Track Inspector 1",
        "hardware_version": "Raspberry Pi 5",
        "firmware_version": "v1.4.2",
    }
    res_reg = client.post("/api/v1/devices/register", json=reg_payload)
    assert res_reg.status_code == 200
    reg_data = res_reg.json()
    assert "api_key" in reg_data
    api_key = reg_data["api_key"]

    # 2. Exchange API key for JWT access token + refresh token
    token_payload = {
        "device_id": "RPI-E2E-001",
        "api_key": api_key,
    }
    res_token = client.post("/api/v1/devices/token", json=token_payload)
    assert res_token.status_code == 200
    tokens = res_token.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    # 3. Use access token on protected telemetry ingestion
    headers = {"Authorization": f"Bearer {access_token}"}
    tel_payload = {
        "session_id": "ses-e2e-001",
        "device_id": "RPI-E2E-001",
        "samples": [
            {
                "chainage_m": 120.0,
                "speed_mps": 25.0,
                "track_gauge_mm": 1676.0,
                "cant_mm": 2.1,
                "twist_mm_per_m": 1.1,
            }
        ],
    }
    res_tel = client.post("/api/v1/telemetry/batch", json=tel_payload, headers=headers)
    assert res_tel.status_code == 200
    assert res_tel.json()["status"] == "ok"

    # 4. Rotate access token using refresh token
    res_refresh = client.post("/api/v1/devices/refresh", json={"refresh_token": refresh_token})
    assert res_refresh.status_code == 200
    new_tokens = res_refresh.json()
    assert "access_token" in new_tokens
    assert new_tokens["access_token"] != access_token


def test_e2e_video_multipart_and_hls_streaming():
    client = TestClient(app)

    mock_client = MagicMock()
    mock_client.create_multipart_upload.return_value = {"UploadId": "test-upload-123"}
    mock_client.complete_multipart_upload.return_value = {"Location": "http://localhost:9000/trackchain-media/videos/test.mp4"}
    mock_client.generate_presigned_url.return_value = "http://localhost:9000/presigned-part"

    with patch("src.services.s3.s3_service.get_client", return_value=mock_client), \
         patch("src.services.s3.s3_service.generate_presigned_get", return_value="http://localhost:9000/trackchain-media/hls/med-e2e-01/master.m3u8?mock=true"):

        # 1. Initiate multipart upload
        init_payload = {
            "session_id": "ses-e2e-video",
            "device_id": "RPI-E2E-001",
            "filename": "track_section_km102.mp4",
            "content_type": "video/mp4",
            "num_parts": 3,
        }
        res_init = client.post("/api/v1/media/multipart/initiate", json=init_payload)
        assert res_init.status_code == 200
        init_data = res_init.json()
        media_id = init_data["media_id"]
        upload_id = init_data["upload_id"]

        # 2. Complete multipart upload
        complete_payload = {
            "media_id": media_id,
            "upload_id": upload_id,
            "parts": [{"PartNumber": 1, "ETag": '"etag1"'}, {"PartNumber": 2, "ETag": '"etag2"'}],
            "size_bytes": 52428800,
            "duration_seconds": 120.0,
        }
        res_comp = client.post("/api/v1/media/multipart/complete", json=complete_payload)
        assert res_comp.status_code == 200
        assert res_comp.json()["upload_status"] == "transcoded"

        # 3. Query media status
        res_status = client.get(f"/api/v1/media/{media_id}/status")
        assert res_status.status_code == 200
        assert res_status.json()["upload_status"] == "transcoded"

        # 4. Fetch HLS master stream URL
        res_hls = client.get(f"/api/v1/media/{media_id}/hls-url")
        assert res_hls.status_code == 200
        hls_data = res_hls.json()
        assert "hls_url" in hls_data
        assert "master.m3u8" in hls_data["hls_url"]


def test_e2e_ml_defect_flow_and_dashboard_summary():
    client = TestClient(app)
    db = SessionLocal()

    # Create session with track_section required field
    ses = MonitoringSession(id="ses-e2e-ml", name="Inspection Section 4", track_id="IR-MAIN-04", track_section="Km 100-110")
    db.add(ses)
    db.commit()
    db.close()

    # Ingest defect with ML signals
    defect_payload = {
        "session_id": "ses-e2e-ml",
        "device_id": "RPI-E2E-001",
        "defect_class": "missing_fastener",
        "severity": "critical",
        "confidence": 0.94,
        "chainage_m": 450.0,
        "latitude": 28.5355,
        "longitude": 77.2842,
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
                "bbox": [100.0, 200.0, 150.0, 250.0],
            }
        ],
    }
    res_defect = client.post("/api/v1/defects", json=defect_payload)
    assert res_defect.status_code == 200
    defect_data = res_defect.json()
    assert defect_data["defect_class"] == "missing_fastener"
    assert defect_data["severity"] == "critical"

    # Verify dashboard KPI aggregation
    res_dash = client.get("/api/v1/dashboard/summary")
    assert res_dash.status_code == 200
    dash_data = res_dash.json()
    assert dash_data["total_defects"] >= 1
    assert dash_data["critical_defects"] >= 1


def test_e2e_device_revocation_blocks_access():
    client = TestClient(app)

    # 1. Register device
    reg_res = client.post("/api/v1/devices/register", json={"device_id": "RPI-REVOKE-01", "name": "Compromised Node"})
    api_key = reg_res.json()["api_key"]

    # 2. Revoke device
    rev_res = client.post("/api/v1/devices/revoke?device_id=RPI-REVOKE-01")
    assert rev_res.status_code == 200
    assert rev_res.json()["status"] == "revoked"

    # 3. Attempting to exchange token now fails with 403
    token_res = client.post("/api/v1/devices/token", json={"device_id": "RPI-REVOKE-01", "api_key": api_key})
    assert token_res.status_code == 403
