"""
ml/tests/test_confidence_fusion.py
Validates Confidence-Weighted Fusion scoring across model streams.
"""

import pytest

from ml.fusion.rules import ConfidenceWeightedFusion
from ml.core.schema import SegmentSignals, CalibratedSignal, SignalType, DefectClass


def test_confidence_weighted_fusion_calculation():
    """Verify that firing models contribute according to their predefined safety weights."""
    fusion = ConfidenceWeightedFusion()

    signals = SegmentSignals(
        v_known=[
            CalibratedSignal(
                stream_name="yolo",
                signal_type=SignalType.VISUAL_KNOWN,
                raw_score=0.90,
                calibrated_prob=0.90,
                is_anomaly=True,
            )
        ],
        g_known=[
            CalibratedSignal(
                stream_name="physics",
                signal_type=SignalType.GEOMETRY_KNOWN,
                raw_score=0.80,
                calibrated_prob=0.80,
                is_anomaly=True,
            )
        ],
    )

    # Weights: YOLO=1.0, Physics=1.2
    # Expected weighted score = (0.90 * 1.0 + 0.80 * 1.2) / (1.0 + 1.2) = (0.90 + 0.96) / 2.2 = 1.86 / 2.2 = 0.84545
    weighted_score = fusion.compute_weighted_score(signals)

    assert pytest.approx(weighted_score, rel=1e-3) == 0.84545


def test_confidence_weighted_fusion_empty_when_no_signals():
    """Verify that 0.0 is returned when no signals are active."""
    fusion = ConfidenceWeightedFusion()
    signals = SegmentSignals()
    assert fusion.compute_weighted_score(signals) == 0.0
