"""
ml/tests/test_cross_modal_boost.py
Validates Cross-Modal Correlation Boost (1.5x severity/confidence boost when vision + geometry corroborate).
"""

import pytest

from ml.fusion.rules import compute_cross_modal_boost, TrackChainFusionEngine
from ml.core.schema import SegmentSignals, CalibratedSignal, SignalType, DefectClass, SeverityLevel, DecisionType


def test_cross_modal_boost_logic():
    """Verify 1.5x boost when vision and geometry both fire."""
    sig_vision = CalibratedSignal(stream_name="yolo", signal_type=SignalType.VISUAL_KNOWN, raw_score=0.9, calibrated_prob=0.9, is_anomaly=True)
    sig_geom = CalibratedSignal(stream_name="physics", signal_type=SignalType.GEOMETRY_KNOWN, raw_score=0.8, calibrated_prob=0.8, is_anomaly=True)

    # 1. Both fire -> 1.5
    dual_signals = SegmentSignals(v_known=[sig_vision], g_known=[sig_geom])
    assert compute_cross_modal_boost(dual_signals) == 1.5

    # 2. Only vision fires -> 1.0
    vis_only = SegmentSignals(v_known=[sig_vision])
    assert compute_cross_modal_boost(vis_only) == 1.0

    # 3. Neither fires -> 0.0
    none_fired = SegmentSignals()
    assert compute_cross_modal_boost(none_fired) == 0.0


def test_cross_modal_boost_elevates_decision_severity():
    """Verify that cross-modal corroboration elevates severity in TrackChainFusionEngine."""
    engine = TrackChainFusionEngine()

    sig_yolo = CalibratedSignal(
        stream_name="yolo",
        signal_type=SignalType.VISUAL_KNOWN,
        predicted_class=DefectClass.MISSING_FASTENER,
        raw_score=0.85,
        calibrated_prob=0.85,
        is_anomaly=True,
    )
    sig_physics = CalibratedSignal(
        stream_name="physics",
        signal_type=SignalType.GEOMETRY_KNOWN,
        predicted_class=DefectClass.TWIST_EXCEEDANCE,
        raw_score=0.75,
        calibrated_prob=0.75,
        is_anomaly=True,
    )

    signals = SegmentSignals(v_known=[sig_yolo], g_known=[sig_physics])
    decision = engine.fuse(signals)

    assert decision.decision == DecisionType.INSPECT_KNOWN
    assert decision.cross_modal_boost == 1.5
    assert decision.severity in (SeverityLevel.HIGH, SeverityLevel.CRITICAL)
