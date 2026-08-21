"""
ml/tests/test_final_backend_roundtrip.py
Category F: Backend Round-Trip Contract Test (tc.v1 SOTA).
Verifies that SegmentDecision objects serialize to valid JSON payloads conforming to the tc.v1 schema, maintaining field integrity across the ML -> API -> DB contract.
"""

import sys
import json
import pytest
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from ml.core.schema import (
    SegmentDecision,
    CalibratedSignal,
    SignalType,
    DefectClass,
    DecisionType,
    SeverityLevel,
    SCHEMA_VERSION,
)


def test_segment_decision_serialization_schema_v1():
    """Verify SegmentDecision serializes cleanly with schema_version == 'tc.v1'."""
    sig = CalibratedSignal(
        name="yolo_missing_fastener",
        stream_name="vision_yolo",
        model_version="0.1.0",
        signal_type=SignalType.VISUAL_KNOWN,
        value=0.88,
        raw_score=0.88,
        calibrated_prob=0.88,
        threshold=0.50,
        fired=True,
        is_anomaly=True,
        predicted_class=DefectClass.MISSING_FASTENER,
        bbox=(100, 150, 200, 250),
        explanation={"confidence": 0.88},
    )

    decision = SegmentDecision(
        window_id="win-00100-00120",
        chainage_start_m=100.0,
        chainage_end_m=120.0,
        decision=DecisionType.INSPECT_KNOWN,
        severity=SeverityLevel.HIGH,
        primary_defect=DefectClass.MISSING_FASTENER,
        confidence=0.88,
        signals=[sig],
        action="Dispatch permanent way maintenance team for immediate fastener replacement.",
        section_type="mainline_standard",
    )

    payload = decision.to_dict()
    assert payload["schema_version"] == "tc.v1"
    assert payload["window_id"] == "win-00100-00120"
    assert payload["chainage_start_m"] == 100.0
    assert payload["chainage_end_m"] == 120.0
    assert payload["decision"] == "INSPECT_KNOWN"
    assert payload["severity"] == "high"
    assert payload["primary_defect"] == "missing_fastener"
    assert payload["confidence"] == 0.88

    # JSON serialization
    json_str = json.dumps(payload, indent=2)
    deserialized = json.loads(json_str)
    assert deserialized["schema_version"] == SCHEMA_VERSION
    assert len(deserialized["signals"]) == 1
    assert deserialized["signals"][0]["bbox"] == [100, 150, 200, 250]


def test_serialization_idempotency():
    """Verify serializing the same SegmentDecision repeatedly yields identical payload strings."""
    decision = SegmentDecision(
        window_id="win-00000-00020",
        chainage_start_m=0.0,
        chainage_end_m=20.0,
        decision=DecisionType.OK,
        severity=SeverityLevel.NORMAL,
        confidence=0.95,
        action="Track clear. Routine inspection cycle maintained.",
    )

    p1 = json.dumps(decision.to_dict(), sort_keys=True)
    p2 = json.dumps(decision.to_dict(), sort_keys=True)
    assert p1 == p2
