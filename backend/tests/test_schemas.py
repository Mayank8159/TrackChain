# Unit tests for tc.v1 Pydantic schemas validation.

from datetime import datetime
from src.schemas.common import SCHEMA_VERSION
from src.schemas.devices import DeviceCreate, DeviceResponse
from src.schemas.sessions import SessionStartRequest, SessionResponse
from src.schemas.segments import TrackSegmentCreate
from src.schemas.telemetry import TelemetrySampleCreate, TelemetryBatchIngestRequest
from src.schemas.media import PresignUploadRequest, PresignUploadResponse
from src.schemas.ml import MLSignalCreate, MLSignalBatchRequest, SegmentDecisionPayload
from src.schemas.defects import DefectEventCreate, DefectEventResponse
from src.schemas.dashboard import DashboardSummaryResponse


def test_schema_version_is_tc_v1():
    assert SCHEMA_VERSION == "tc.v1"


def test_device_schema():
    dev = DeviceCreate(
        device_id="RPI-ITMS-001",
        device_name="Trolley Alpha",
        hardware_version="RPi 5 8GB",
        firmware_version="0.1.0",
    )
    assert dev.device_id == "RPI-ITMS-001"


def test_session_start_schema():
    ses = SessionStartRequest(
        name="NDLS-AGC Test Run",
        track_id="IR-NR-01",
        track_section="New Delhi to Mathura",
    )
    assert ses.track_direction == "both"


def test_telemetry_batch_ingest_schema():
    batch = TelemetryBatchIngestRequest(
        idempotency_key="idemp-12345",
        session_id="ses-001",
        samples=[
            TelemetrySampleCreate(
                chainage_m=100.5,
                speed_mps=25.0,
                track_gauge_mm=1435.2,
                cant_mm=5.0,
                twist_mm_per_m=0.8,
            )
        ],
    )
    assert batch.schema_version == "tc.v1"
    assert len(batch.samples) == 1


def test_ml_signal_batch_schema():
    ml_batch = MLSignalBatchRequest(
        idempotency_key="idemp-67890",
        session_id="ses-001",
        segment_id="seg-001",
        signals=[
            MLSignalCreate(
                model_name="yolo_v8_detector",
                model_version="0.1.0",
                signal_type="visual_known",
                raw_score=0.95,
                calibrated_score=0.91,
                threshold=0.50,
                fired=True,
                label="missing_fastener",
                bbox=[100.0, 150.0, 200.0, 250.0],
            )
        ],
    )
    assert ml_batch.signals[0].fired is True
    assert ml_batch.signals[0].label == "missing_fastener"


def test_defect_create_schema():
    defect = DefectEventCreate(
        session_id="ses-001",
        chainage_m=12450.0,
        defect_class="missing_fastener",
        defect_family="visual_component",
        severity="critical",
        confidence=0.94,
        source_model="yolo_v8_detector",
    )
    assert defect.decision == "INSPECT_KNOWN"
    assert defect.status == "open"


def test_dashboard_summary_schema():
    dash = DashboardSummaryResponse(
        total_defects=10,
        critical_defects=2,
        distance_covered_km=140.0,
        avg_speed_kmh=110.5,
        open_alerts=1,
        defect_counts_by_class={"missing_fastener": 5, "crack": 5},
        severity_distribution={"critical": 2, "high": 3, "medium": 3, "low": 2},
    )
    assert dash.total_defects == 10
