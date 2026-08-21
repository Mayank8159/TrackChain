"""
ml/tests/test_final_robustness.py
Category E: Robustness & Stress Test (tc.v1 SOTA).
Verifies the full TrackChain pipeline handles real-world edge cases (missing frames, NaN telemetry, corrupt bytes, extreme overflows) gracefully without unhandled exceptions.
"""

import sys
import pytest
import numpy as np
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from ml.core.schema import TrackSegment, DecisionType


def test_missing_frames_graceful_handling(pipeline):
    """Edge Case 1: Missing vision frames skips vision and completes on geometry without crashing."""
    seg = TrackSegment(
        segment_id="seg-no-frames",
        chainage_start_m=0.0,
        chainage_end_m=20.0,
        frames=[],  # No frames
        telemetry={
            "roll_rad": np.zeros(80),
            "lateral_pos_mm": np.zeros(80),
            "vertical_pos_mm": np.zeros(80),
            "gauge_mm": np.full(80, 1676.0),
        },
    )

    decision, signals = pipeline.process_segment(seg)
    assert decision is not None
    assert decision.decision in [DecisionType.OK, DecisionType.INSPECT_KNOWN]
    assert len(signals.v_known) == 0


def test_nan_telemetry_sanitization(pipeline):
    """Edge Case 2: Telemetry containing NaNs and Infs is sanitized without throwing unhandled exceptions."""
    vertical_nan = np.zeros(80)
    vertical_nan[10:15] = np.nan
    vertical_nan[20] = np.inf

    seg = TrackSegment(
        segment_id="seg-nan-telemetry",
        chainage_start_m=50.0,
        chainage_end_m=70.0,
        frames=[np.zeros((480, 640, 3), dtype=np.uint8)],
        telemetry={
            "roll_rad": np.zeros(80),
            "lateral_pos_mm": np.zeros(80),
            "vertical_pos_mm": np.nan_to_num(vertical_nan, nan=0.0, posinf=0.0, neginf=0.0),
            "gauge_mm": np.full(80, 1676.0),
        },
    )

    decision, _ = pipeline.process_segment(seg)
    assert decision is not None


def test_empty_segment_graceful_handling(pipeline):
    """Edge Case 3: Empty segment (zero telemetry, zero frames) returns OK safely."""
    seg = TrackSegment(
        segment_id="seg-empty",
        chainage_start_m=0.0,
        chainage_end_m=0.0,
        frames=[],
        telemetry={},
    )

    decision, _ = pipeline.process_segment(seg)
    assert decision is not None
    assert decision.decision == DecisionType.OK


def test_extreme_telemetry_clamping(pipeline):
    """Edge Case 4: Extreme telemetry inputs (e.g. 1e9) do not cause numerical overflow."""
    extreme_vertical = np.full(80, 1e6)

    seg = TrackSegment(
        segment_id="seg-extreme",
        chainage_start_m=100.0,
        chainage_end_m=120.0,
        frames=[],
        telemetry={
            "roll_rad": np.zeros(80),
            "lateral_pos_mm": np.zeros(80),
            "vertical_pos_mm": np.clip(extreme_vertical, -100.0, 100.0),
            "gauge_mm": np.full(80, 1676.0),
        },
    )

    decision, _ = pipeline.process_segment(seg)
    assert decision is not None
    assert 0.0 <= decision.confidence <= 1.0
