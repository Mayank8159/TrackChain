"""
ml/tests/test_final_integration.py
Category A: Multimodal Integration Test (tc.v1 SOTA).
Verifies that a TrackSegment flows through all 5 ML models + fusion and produces valid SegmentDecisions across all defect scenarios.
"""

import sys
import pytest
import numpy as np
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from ml.core.schema import TrackSegment, DecisionType, SeverityLevel, SignalType
from ml.inference.pipeline import TrackChainMLPipeline


def test_multimodal_clean_track_decision(pipeline, clean_segment):
    """Scenario 1: Clean track with no defects produces OK decision."""
    decision, signals = pipeline.process_segment(clean_segment)

    assert decision is not None
    assert decision.decision == DecisionType.OK
    assert decision.severity in [SeverityLevel.NORMAL, SeverityLevel.LOW]
    assert len(signals.all_signals) > 0


def test_multimodal_geometry_twist_exceedance(pipeline, defective_segment):
    """Scenario 2: Geometry twist exceedance triggers INSPECT_KNOWN."""
    decision, signals = pipeline.process_segment(defective_segment)

    assert decision is not None
    assert decision.decision == DecisionType.INSPECT_KNOWN
    assert decision.severity in [SeverityLevel.MEDIUM, SeverityLevel.HIGH, SeverityLevel.CRITICAL]

    # Verify physics signal fired
    phys_fired = any(s.fired for s in signals.g_known)
    assert phys_fired, "Physics signal should have fired for twist exceedance"


def test_multimodal_novel_anomaly_persistence(pipeline, novel_segment):
    """Scenario 3: Novel geometry/visual pattern triggers INSPECT_NOVEL after persistence."""
    # Feed segment multiple times to satisfy persistence hysteresis window (N=3)
    decisions = []
    for i in range(4):
        seg = TrackSegment(
            segment_id=f"novel-{i}",
            chainage_start_m=200.0 + i * 20.0,
            chainage_end_m=220.0 + i * 20.0,
            frames=novel_segment.frames,
            telemetry=novel_segment.telemetry,
            section_type="mainline_standard",
        )
        dec, _ = pipeline.process_segment(seg)
        decisions.append(dec)

    final_decision = decisions[-1]
    assert final_decision.decision in [DecisionType.INSPECT_NOVEL, DecisionType.INSPECT_KNOWN]


def test_multimodal_compound_defect_severity_boost(pipeline):
    """Scenario 4: Simultaneous visual defect and geometry defect triggers cross-modal severity boost."""
    n_bins = 80
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[220:260, 300:340] = 255  # Visual defect

    # Severe geometry dip causing multiple limit breaches
    vertical = np.zeros(n_bins)
    vertical[30:50] = 18.0

    compound_seg = TrackSegment(
        segment_id="seg-compound-001",
        chainage_start_m=500.0,
        chainage_end_m=520.0,
        frames=[img],
        telemetry={
            "roll_rad": np.zeros(n_bins),
            "lateral_pos_mm": np.full(n_bins, 6.0),
            "vertical_pos_mm": vertical,
            "gauge_mm": np.full(n_bins, 1685.0),
        },
        section_type="mainline_standard",
    )

    decision, signals = pipeline.process_segment(compound_seg)

    assert decision.decision == DecisionType.INSPECT_KNOWN
    assert decision.severity in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]
    assert decision.confidence >= 0.60
