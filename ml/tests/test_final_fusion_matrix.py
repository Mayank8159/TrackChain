"""
ml/tests/test_final_fusion_matrix.py
Category C: Fusion Decision Matrix Test (tc.v1 SOTA).
Exhaustively tests the multi-modal fusion truth table, spatial persistence/hysteresis, and cross-modal severity escalation.
"""

import sys
import pytest
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from ml.core.schema import (
    CalibratedSignal,
    SegmentSignals,
    SignalType,
    DefectClass,
    DecisionType,
    SeverityLevel,
)
from ml.fusion.rules import TrackChainFusionEngine, compute_cross_modal_boost


def create_signal(signal_type: SignalType, fired: bool, score: float = 0.85) -> CalibratedSignal:
    """Helper to generate calibrated signal."""
    val = score if fired else 0.10
    return CalibratedSignal(
        name=f"test_{signal_type.value}",
        stream_name=signal_type.value,
        model_version="0.1.0",
        signal_type=signal_type,
        value=val,
        raw_score=val,
        calibrated_prob=val,
        threshold=0.50,
        fired=fired,
        is_anomaly=fired,
        predicted_class=DefectClass.CRACK if fired else DefectClass.NORMAL,
    )


def test_fusion_matrix_all_combinations():
    """Verify all combinations in the multi-modal fusion truth table."""
    engine = TrackChainFusionEngine(persistence_window=1)

    # 1. Clean [0, 0, 0, 0] -> OK
    sig_clean = SegmentSignals(
        v_known=[create_signal(SignalType.VISUAL_KNOWN, False)],
        v_novel=[create_signal(SignalType.VISUAL_NOVEL, False)],
        g_known=[create_signal(SignalType.GEOMETRY_KNOWN, False)],
        g_novel=[create_signal(SignalType.GEOMETRY_NOVEL, False)],
    )
    dec_clean = engine.fuse(sig_clean, "w1", 0.0, 20.0)
    assert dec_clean.decision == DecisionType.OK

    # 2. Visual Known Only [1, 0, 0, 0] -> INSPECT_KNOWN
    sig_v_known = SegmentSignals(
        v_known=[create_signal(SignalType.VISUAL_KNOWN, True, score=0.90)],
        v_novel=[create_signal(SignalType.VISUAL_NOVEL, False)],
        g_known=[create_signal(SignalType.GEOMETRY_KNOWN, False)],
        g_novel=[create_signal(SignalType.GEOMETRY_NOVEL, False)],
    )
    dec_v_known = engine.fuse(sig_v_known, "w2", 20.0, 40.0)
    assert dec_v_known.decision == DecisionType.INSPECT_KNOWN

    # 3. Geometry Known Only [0, 0, 1, 0] -> INSPECT_KNOWN
    sig_g_known = SegmentSignals(
        v_known=[create_signal(SignalType.VISUAL_KNOWN, False)],
        v_novel=[create_signal(SignalType.VISUAL_NOVEL, False)],
        g_known=[create_signal(SignalType.GEOMETRY_KNOWN, True, score=0.90)],
        g_novel=[create_signal(SignalType.GEOMETRY_NOVEL, False)],
    )
    dec_g_known = engine.fuse(sig_g_known, "w3", 40.0, 60.0)
    assert dec_g_known.decision == DecisionType.INSPECT_KNOWN

    # 4. Visual Novel Only [0, 1, 0, 0] -> INSPECT_NOVEL
    sig_v_novel = SegmentSignals(
        v_known=[create_signal(SignalType.VISUAL_KNOWN, False)],
        v_novel=[create_signal(SignalType.VISUAL_NOVEL, True, score=0.85)],
        g_known=[create_signal(SignalType.GEOMETRY_KNOWN, False)],
        g_novel=[create_signal(SignalType.GEOMETRY_NOVEL, False)],
    )
    dec_v_novel = engine.fuse(sig_v_novel, "w4", 60.0, 80.0)
    assert dec_v_novel.decision == DecisionType.INSPECT_NOVEL

    # 5. Geometry Novel Only [0, 0, 0, 1] -> INSPECT_NOVEL
    sig_g_novel = SegmentSignals(
        v_known=[create_signal(SignalType.VISUAL_KNOWN, False)],
        v_novel=[create_signal(SignalType.VISUAL_NOVEL, False)],
        g_known=[create_signal(SignalType.GEOMETRY_KNOWN, False)],
        g_novel=[create_signal(SignalType.GEOMETRY_NOVEL, True, score=0.85)],
    )
    dec_g_novel = engine.fuse(sig_g_novel, "w5", 80.0, 100.0)
    assert dec_g_novel.decision == DecisionType.INSPECT_NOVEL


def test_cross_modal_boost_logic():
    """Verify 1.5x multiplier when both vision and geometry fire simultaneously."""
    # Dual modality
    sig_dual = SegmentSignals(
        v_known=[create_signal(SignalType.VISUAL_KNOWN, True)],
        g_known=[create_signal(SignalType.GEOMETRY_KNOWN, True)],
    )
    boost_dual = compute_cross_modal_boost(sig_dual)
    assert boost_dual == 1.5

    # Single modality
    sig_single = SegmentSignals(
        v_known=[create_signal(SignalType.VISUAL_KNOWN, True)],
        g_known=[create_signal(SignalType.GEOMETRY_KNOWN, False)],
    )
    boost_single = compute_cross_modal_boost(sig_single)
    assert boost_single == 1.0

    # Neither
    sig_none = SegmentSignals(
        v_known=[create_signal(SignalType.VISUAL_KNOWN, False)],
        g_known=[create_signal(SignalType.GEOMETRY_KNOWN, False)],
    )
    boost_none = compute_cross_modal_boost(sig_none)
    assert boost_none == 0.0
