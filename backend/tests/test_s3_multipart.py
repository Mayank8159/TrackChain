# Tests for S3 Multipart Upload and Media Streaming endpoints (tc.v1 SOTA).

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from src.main import app
from src.db.session import Base, engine


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield


def test_multipart_upload_workflow():
    client = TestClient(app)

    # 1. Initiate multipart upload
    initiate_payload = {
        "session_id": "ses-multipart-001",
        "device_id": "RPI-01",
        "media_type": "video_segment",
        "filename": "camera_front_km10.mp4",
        "content_type": "video/mp4",
        "num_parts": 10,
        "size_bytes": 52428800,
        "chainage_start_m": 10000.0,
        "chainage_end_m": 10500.0,
    }

    mock_init_return = {
        "upload_id": "mock-upload-id-999",
        "s3_bucket": "trackchain-media",
        "s3_key": "videos/ses-multipart-001/camera_front_km10.mp4",
        "num_parts": 10,
        "parts": [
            {"part_number": i, "upload_url": f"http://localhost:9000/trackchain-media/videos/ses-multipart-001/camera_front_km10.mp4?partNumber={i}&uploadId=mock-upload-id-999"}
            for i in range(1, 11)
        ],
    }

    with patch("src.services.s3.s3_service.initiate_multipart_upload", return_value=mock_init_return):
        res_init = client.post("/api/v1/media/multipart/initiate", json=initiate_payload)
        assert res_init.status_code == 200
        data_init = res_init.json()
        assert data_init["upload_id"] == "mock-upload-id-999"
        assert "media_id" in data_init
        assert data_init["num_parts"] == 10
        assert len(data_init["parts"]) == 10
        assert data_init["parts"][0]["part_number"] == 1
        assert "upload_url" in data_init["parts"][0]

    media_id = data_init["media_id"]
    upload_id = data_init["upload_id"]

    # 2. Complete multipart upload
    complete_payload = {
        "media_id": media_id,
        "upload_id": upload_id,
        "parts": [
            {"PartNumber": i, "ETag": f'"etag-mock-{i}"'}
            for i in range(1, 11)
        ],
        "size_bytes": 52428800,
        "duration_seconds": 30.5,
        "checksum": "sha256:multipartmock123",
    }

    mock_comp_return = {
        "status": "completed",
        "s3_bucket": "trackchain-media",
        "s3_key": "videos/ses-multipart-001/camera_front_km10.mp4",
        "location": "http://localhost:9000/trackchain-media/videos/ses-multipart-001/camera_front_km10.mp4",
    }

    with patch("src.services.s3.s3_service.complete_multipart_upload", return_value=mock_comp_return):
        res_comp = client.post("/api/v1/media/multipart/complete", json=complete_payload)
        assert res_comp.status_code == 200
        data_comp = res_comp.json()
        assert data_comp["status"] == "ok"
        assert data_comp["upload_status"] in ("completed", "transcoded")

    # 3. Request presigned streaming URL
    with patch("src.services.s3.s3_service.generate_presigned_get", return_value="http://localhost:9000/trackchain-media/videos/ses-multipart-001/camera_front_km10.mp4?stream-token=mock"):
        res_url = client.get(f"/api/v1/media/{media_id}/url")
        assert res_url.status_code == 200
        assert "download_url" in res_url.json()
        assert res_url.json()["media_id"] == media_id
