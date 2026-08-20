# Unit tests for multi-sensor fusion and persistence rules (tc.v1).

import pytest
from ml.fusion.rules import PersistenceRuleFusion
from ml.core.schema import CalibratedSignal, DecisionType, DefectClass


def test_nominal_signals_fuse_to_ok():
    fusion = PersistenceRuleFusion(persistence_window=1)
    signals = [
        CalibratedSignal("vision_detector", raw_score=0.1, calibrated_prob=0.05, is_anomaly=False),
        CalibratedSignal("geometry_lstm", raw_score=0.2, calibrated_prob=0.10, is_anomaly=False),
    ]
    decision = fusion.fuse(
        window_id="w-001",
        start_chainage_m=100.0,
        end_chainage_m=102.0,
        signals=signals,
    )
    assert decision.decision == DecisionType.OK


def test_known_defect_fuses_to_inspect_known():
    fusion = PersistenceRuleFusion(persistence_window=1)
    signals = [
        CalibratedSignal(
            "vision_detector",
            raw_score=0.95,
            calibrated_prob=0.91,
            predicted_class=DefectClass.MISSING_FASTENER,
            is_anomaly=True,
        ),
    ]
    decision = fusion.fuse(
        window_id="w-002",
        start_chainage_m=102.0,
        end_chainage_m=104.0,
        signals=signals,
    )
    assert decision.decision == DecisionType.INSPECT_KNOWN
    assert decision.primary_fault == DefectClass.MISSING_FASTENER
