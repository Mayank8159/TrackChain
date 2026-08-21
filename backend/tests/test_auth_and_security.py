# Tests for JWT Device Authentication, Token Bucket Rate Limiting, and HMAC Request Signing (tc.v1 SOTA).

import time
import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.db.session import Base, engine
from src.services.auth import auth_service, hash_api_key
from src.services.rate_limiter import RateLimiter
from src.services.request_signing import RequestSigner


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield


def test_device_registration_and_jwt_token_exchange():
    client = TestClient(app)

    # 1. Register new edge device
    reg_payload = {
        "device_id": "RPI-SECURITY-01",
        "device_name": "Secure Edge Node 1",
        "hardware_version": "Raspberry Pi 5",
        "firmware_version": "v1.2.0",
    }
    reg_res = client.post("/api/v1/devices/register", json=reg_payload)
    assert reg_res.status_code == 200
    reg_data = reg_res.json()
    assert "api_key" in reg_data
    assert reg_data["device_id"] == "RPI-SECURITY-01"
    api_key = reg_data["api_key"]

    # 2. Exchange API key for short-lived JWT
    token_payload = {
        "device_id": "RPI-SECURITY-01",
        "api_key": api_key,
    }
    token_res = client.post("/api/v1/devices/token", json=token_payload)
    assert token_res.status_code == 200
    token_data = token_res.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    # 3. Verify JWT token claims
    claims = auth_service.verify_token(token_data["access_token"])
    assert claims["sub"] == "RPI-SECURITY-01"
    assert "telemetry:write" in claims["scopes"]


def test_token_bucket_rate_limiter():
    limiter = RateLimiter(requests_per_minute=60, burst_size=3)

    # First 3 calls succeed (consume burst tokens)
    assert limiter.check_rate_limit_sync("device-test-1") is True
    assert limiter.check_rate_limit_sync("device-test-1") is True
    assert limiter.check_rate_limit_sync("device-test-1") is True

    # 4th immediate call is throttled
    assert limiter.check_rate_limit_sync("device-test-1") is False


def test_hmac_request_signing():
    signer = RequestSigner(secret_key="test-secret-key", tolerance_seconds=300)
    body = b'{"session_id":"ses-123","samples":[]}'
    timestamp = str(int(time.time()))

    # Compute valid signature
    sig = signer.compute_signature("POST", "/api/v1/telemetry/batch", timestamp, body)

    # Valid signature check
    assert signer.verify_signature("POST", "/api/v1/telemetry/batch", timestamp, sig, body) is True

    # Tampered body check fails
    tampered_body = b'{"session_id":"ses-123","samples":[{"tampered":true}]}'
    assert signer.verify_signature("POST", "/api/v1/telemetry/batch", timestamp, sig, tampered_body) is False

    # Expired timestamp check (> 300s old) fails
    old_timestamp = str(int(time.time()) - 600)
    old_sig = signer.compute_signature("POST", "/api/v1/telemetry/batch", old_timestamp, body)
    assert signer.verify_signature("POST", "/api/v1/telemetry/batch", old_timestamp, old_sig, body) is False
