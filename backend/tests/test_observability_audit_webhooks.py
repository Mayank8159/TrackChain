# Tests for Phase 3.5 Observability (Prometheus + Tracing), Audit Logging, Webhooks & Circuit Breakers (tc.v1 SOTA).

import asyncio
import time
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from src.main import app
from src.db.session import Base, engine, SessionLocal
from src.db.models import AuditLog, MonitoringSession
from src.services.observability import (
    REQUEST_COUNT,
    DEFECTS_CREATED,
    TELEMETRY_SAMPLES_INGESTED,
    logger,
    get_current_request_id,
)
from src.services.audit import AuditService, audit_service
from src.services.webhooks import WebhookService, webhook_service
from src.services.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerOpenError,
)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield


def test_observability_metrics_and_request_tracing():
    client = TestClient(app)

    # 1. Send request with custom X-Request-ID
    custom_trace_id = "trace-inspection-999"
    res = client.get("/health", headers={"X-Request-ID": custom_trace_id})
    assert res.status_code == 200
    assert res.headers.get("X-Request-ID") == custom_trace_id

    # 2. Send request without X-Request-ID and verify auto-generation
    res_auto = client.get("/health")
    assert res_auto.status_code == 200
    assert "X-Request-ID" in res_auto.headers
    assert res_auto.headers["X-Request-ID"].startswith("req_")

    # 3. Query Prometheus metrics endpoint
    res_metrics = client.get("/metrics")
    assert res_metrics.status_code == 200
    assert "trackchain_http_requests_total" in res_metrics.text
    assert "trackchain_http_request_duration_seconds" in res_metrics.text
    assert "trackchain_defects_created_total" in res_metrics.text


def test_audit_logging_service_and_db_persistence():
    db = SessionLocal()

    # 1. Directly record an audit log entry
    audit_entry = AuditService.log_sync(
        actor_type="user",
        actor_id="inspector_verma",
        action="track_section.certified",
        resource_type="track_section",
        resource_id="IR-NR-KM104",
        details={"gauge_status": "nominal", "quality_index": 98.4},
        ip_address="192.168.1.100",
        db=db,
    )
    assert audit_entry is not None
    assert audit_entry.id is not None
    assert audit_entry.actor_id == "inspector_verma"
    assert audit_entry.action == "track_section.certified"

    # Query DB to verify persistence
    persisted = db.query(AuditLog).filter(AuditLog.id == audit_entry.id).first()
    assert persisted is not None
    assert persisted.resource_id == "IR-NR-KM104"
    assert persisted.details["quality_index"] == 98.4
    db.close()


def test_device_registration_and_defect_automatic_audit_trail():
    client = TestClient(app)
    db = SessionLocal()

    # 1. Register device
    dev_id = "RPI-AUDIT-001"
    reg_res = client.post(
        "/api/v1/devices/register",
        json={"device_id": dev_id, "name": "Audit Inspection Cart", "hardware_version": "RPi 5"},
    )
    assert reg_res.status_code == 200

    # Verify audit log for device registration
    audit_dev = (
        db.query(AuditLog)
        .filter(AuditLog.actor_type == "system", AuditLog.action == "device.registered", AuditLog.resource_id == dev_id)
        .first()
    )
    assert audit_dev is not None
    assert audit_dev.details["device_name"] == "Audit Inspection Cart"

    # 2. Ingest defect event
    ses = MonitoringSession(id="ses-audit-test", name="Audit Section", track_id="IR-AUDIT-01", track_section="Km 1-5")
    db.add(ses)
    db.commit()

    defect_res = client.post(
        "/api/v1/defects",
        json={
            "session_id": "ses-audit-test",
            "device_id": dev_id,
            "defect_class": "squat",
            "severity": "high",
            "confidence": 0.92,
            "chainage_m": 250.0,
            "latitude": 28.6139,
            "longitude": 77.2090,
        },
    )
    assert defect_res.status_code == 200
    defect_id = defect_res.json()["id"]

    # Verify audit log for defect creation
    audit_def = (
        db.query(AuditLog)
        .filter(AuditLog.action == "defect.created", AuditLog.resource_id == defect_id)
        .first()
    )
    assert audit_def is not None
    assert audit_def.details["defect_class"] == "squat"
    assert audit_def.details["severity"] == "high"
    db.close()


@pytest.mark.anyio
async def test_webhook_signature_and_delivery_retry():
    wh = WebhookService()
    secret = "rdso-test-secret-key-123"
    payload_str = '{"data":{"defect_id":"def-123"},"event_type":"defect.critical"}'

    # 1. Check signature generation
    signature = wh.sign_payload(payload_str, secret)
    assert isinstance(signature, str)
    assert len(signature) == 64  # SHA256 hex length

    # 2. Send webhook to unconfigured URL (should gracefully skip without error)
    result_skip = await wh.send_alert(
        system="rdso",
        event_type="defect.critical",
        payload={"defect_id": "def-123"},
    )
    assert result_skip["status"] == "skipped"

    # 3. Test mock webhook delivery with simulated client
    wh.webhook_urls["rdso"] = "https://rdso.railways.gov.in/api/v1/alerts"
    wh.webhook_secrets["rdso"] = secret

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        result_delivered = await wh.send_alert(
            system="rdso",
            event_type="defect.critical",
            payload={"defect_id": "def-critical-001", "chainage_m": 500.0},
        )
        assert result_delivered["status"] == "delivered"
        assert result_delivered["status_code"] == 200


def test_circuit_breaker_state_transitions_and_degradation():
    breaker = CircuitBreaker(name="test_service", failure_threshold=3, recovery_timeout=0.2)

    counter = {"calls": 0}

    @breaker
    def flaky_external_call(should_fail: bool):
        counter["calls"] += 1
        if should_fail:
            raise ConnectionError("External API down")
        return "success"

    # 1. Normal successful calls keep circuit CLOSED
    assert flaky_external_call(False) == "success"
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0

    # 2. Failures accumulate until threshold
    for _ in range(3):
        with pytest.raises(ConnectionError):
            flaky_external_call(True)

    assert breaker.state == CircuitState.OPEN

    # 3. While OPEN, call fails fast with CircuitBreakerOpenError without executing function
    call_count_before = counter["calls"]
    with pytest.raises(CircuitBreakerOpenError) as exc_info:
        flaky_external_call(False)
    assert counter["calls"] == call_count_before  # Function was NOT executed
    assert exc_info.value.retry_after >= 1

    # 4. Wait for recovery timeout to elapse (state transitions to HALF_OPEN -> CLOSED on success)
    time.sleep(0.25)
    assert flaky_external_call(False) == "success"
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0
