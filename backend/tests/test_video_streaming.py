# Tests for Video Range Streaming (HTTP 206), Thumbnail Generation, and HLS Transcoding (tc.v1 SOTA).

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from src.main import app
from src.db.session import Base, engine, SessionLocal
from src.db.models import MediaAsset


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield


def test_video_range_request_seeking():
    client = TestClient(app)
    db = SessionLocal()

    # Create dummy video media asset
    asset = MediaAsset(
        media_id="med-stream-001",
        session_id="ses-stream-test",
        media_type="video_segment",
        s3_bucket="trackchain-media",
        s3_key="videos/ses-stream-test/track_cam_01.mp4",
        content_type="video/mp4",
        size_bytes=10485760,  # 10MB
        upload_status="completed",
    )
    db.add(asset)
    db.commit()
    db.close()

    # 1. Request with byte range 0-1023 (First 1KB)
    headers = {"Range": "bytes=0-1023"}
    res = client.get("/api/v1/media/med-stream-001/stream", headers=headers)
    assert res.status_code == 206
    assert res.headers["Content-Range"] == "bytes 0-1023/10485760"
    assert res.headers["Accept-Ranges"] == "bytes"
    assert res.headers["Content-Length"] == "1024"
    assert "Location" in res.headers

    # 2. Request without range header -> redirect 302
    with patch("src.services.s3.s3_service.generate_presigned_get", return_value="http://localhost:9000/trackchain-media/videos/ses-stream-test/track_cam_01.mp4?mock=true"):
        res_full = client.get("/api/v1/media/med-stream-001/stream", follow_redirects=False)
        assert res_full.status_code == 302
        assert "Location" in res_full.headers


def test_thumbnail_generation_endpoint():
    client = TestClient(app)
    db = SessionLocal()

    asset = MediaAsset(
        media_id="med-thumb-001",
        session_id="ses-thumb-test",
        media_type="video_segment",
        s3_bucket="trackchain-media",
        s3_key="videos/ses-thumb-test/track_cam_02.mp4",
        content_type="video/mp4",
        upload_status="completed",
    )
    db.add(asset)
    db.commit()
    db.close()

    mock_client = MagicMock()
    with patch("src.services.s3.s3_service.get_client", return_value=mock_client):
        res = client.post("/api/v1/media/med-thumb-001/thumbnail")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "generated"
        assert "thumbnails/med-thumb-001.jpg" in data["thumbnail_key"]


def test_hls_adaptive_transcoding_endpoint():
    client = TestClient(app)
    db = SessionLocal()

    asset = MediaAsset(
        media_id="med-hls-001",
        session_id="ses-hls-test",
        media_type="video_segment",
        s3_bucket="trackchain-media",
        s3_key="videos/ses-hls-test/track_cam_03.mp4",
        content_type="video/mp4",
        upload_status="completed",
    )
    db.add(asset)
    db.commit()
    db.close()

    mock_client = MagicMock()
    with patch("src.services.s3.s3_service.get_client", return_value=mock_client):
        res = client.post("/api/v1/media/med-hls-001/transcode-hls")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "completed"
        assert "master_playlist_key" in data
        assert len(data["renditions"]) == 4
