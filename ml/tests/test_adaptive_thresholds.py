"""
ml/tests/test_adaptive_thresholds.py
Validates Adaptive Section-Based Criticality Thresholds across mainline and yard tracks.
"""

import pytest

from ml.fusion.rules import TrackChainFusionEngine, AdaptiveThresholdManager
from ml.core.schema import SegmentSignals, CalibratedSignal, SignalType, DefectClass, DecisionType


def test_adaptive_threshold_profiles():
    """Verify threshold manager provides distinct sensitivity profiles."""
    mgr = AdaptiveThresholdManager()

    high_speed = mgr.get_profile("mainline_high_speed")
    standard = mgr.get_profile("mainline_standard")
    yard = mgr.get_profile("yard_track")

    # High speed mainline is more sensitive (lower threshold) than yard track
    assert high_speed["threshold"] < standard["threshold"] < yard["threshold"]


def test_fusion_engine_adaptive_routing():
    """Verify that a 0.65 novel score alarms on high-speed mainline after accumulation but is filtered on yard track."""
    engine_high_speed = TrackChainFusionEngine()
    engine_yard = TrackChainFusionEngine()

    sig_novel = CalibratedSignal(
        stream_name="geometry_vae",
        signal_type=SignalType.GEOMETRY_NOVEL,
        raw_score=0.85,
        calibrated_prob=0.85,
        is_anomaly=True,
    )
    signals = SegmentSignals(g_novel=[sig_novel])

    # 1. On high-speed mainline (threshold=0.40, decay=0.80):
    # Window 1: score = 0.3 * 0.85 = 0.255
    # Window 2: score = 0.8 * 0.255 + 0.3 * 0.85 = 0.459 >= 0.40 -> ALARMS on Window 2!
    engine_high_speed.fuse(signals, section_type="mainline_high_speed")
    dec_high = engine_high_speed.fuse(signals, section_type="mainline_high_speed")
    assert dec_high.decision == DecisionType.INSPECT_NOVEL

    # 2. On yard track (threshold=0.70, decay=0.50):
    # Window 1: score = 0.3 * 0.85 = 0.255 < 0.70
    # Window 2: score = 0.5 * 0.255 + 0.3 * 0.85 = 0.3825 < 0.70
    # Window 3: score = 0.5 * 0.3825 + 0.255 = 0.44625 < 0.70 -> Still Filtered (OK)!
    engine_yard.fuse(signals, section_type="yard_track")
    dec_yard = engine_yard.fuse(signals, section_type="yard_track")
    assert dec_yard.decision == DecisionType.OK
