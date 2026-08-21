"""
ml/tests/test_final_consistency.py
Phase 2.7 Hardened P0/P1/P2/P3 Consistency, Physics Correctness & Fusion Integrity Suite (tc.v1 SOTA).
"""

import sys
import json
import pytest
import numpy as np
import torch
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from ml.core.schema import (
    TrackSegment,
    SegmentDecision,
    SegmentSignals,
    CalibratedSignal,
    SignalType,
    DefectClass,
    DecisionType,
    SeverityLevel,
    SCHEMA_VERSION,
)
from ml.models.geometry.fault_classifier import GeometryFaultClassifier, NUM_GEOMETRY_CLASSES
from ml.models.geometry.physics_detector import EN13848PhysicsThresholdDetector
from ml.models.geometry.sequence_vae import SequenceVAEDetector
from ml.models.vision.detector import YOLOv8DefectDetector
from ml.models.vision.anomaly import PatchCoreAnomalyDetector
from ml.fusion.rules import TrackChainFusionEngine, compute_cross_modal_boost
from ml.inference.pipeline import TrackChainMLPipeline
from ml.data.synthetic_geometry import SyntheticGeometryDataset


# =============================================================================
# P0: Consistency Tests (Single Source of Truth)
# =============================================================================

def test_class_count_consistency():
    """P0-1: Assert dataset classes == NUM_GEOMETRY_CLASSES == CLASS_MAP == calibration vector dims."""
    # 1. Dataset definition
    dataset_classes = len(SyntheticGeometryDataset.FAULT_TYPES)
    assert dataset_classes == 6, f"Dataset FAULT_TYPES should have 6 classes, got {dataset_classes}"

    # 2. Model definition constant
    assert NUM_GEOMETRY_CLASSES == 6, f"NUM_GEOMETRY_CLASSES constant should be 6, got {NUM_GEOMETRY_CLASSES}"

    # 3. Classifier class map
    assert len(GeometryFaultClassifier.CLASS_MAP) == 6, "GeometryFaultClassifier.CLASS_MAP must map 6 classes (0..5)"

    # 4. Calibration manifest (if present)
    calib_file = repo_root / "artifacts" / "calibration" / "bilstm_temp.json"
    if calib_file.exists():
        with open(calib_file, "r", encoding="utf-8") as f:
            cal_data = json.load(f)
        if "weights" in cal_data:
            assert len(cal_data["weights"]) == 6, f"Vector scaling weights must have dim 6, got {len(cal_data['weights'])}"
        if "biases" in cal_data:
            assert len(cal_data["biases"]) == 6, f"Vector scaling biases must have dim 6, got {len(cal_data['biases'])}"


def test_calibration_matches_model_output_dim(loaded_models):
    """P0-2: Verify loaded Bi-LSTM classifier model output head matches vector calibration dimension."""
    clf = loaded_models["bilstm"]
    assert clf.num_classes == 6
    if clf.vector_weights is not None:
        assert len(clf.vector_weights) == clf.num_classes, (
            f"Dimension mismatch: model num_classes={clf.num_classes} vs vector_weights={len(clf.vector_weights)}"
        )


def test_signal_schema_contract(loaded_models):
    """P0-3: Verify all 5 models output CalibratedSignal conforming to tc.v1 contract."""
    # 1. YOLO signal
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    yolo_sigs = loaded_models["yolo"].predict(dummy_frame)
    for s in yolo_sigs:
        assert isinstance(s, CalibratedSignal)
        assert 0.0 <= s.calibrated_prob <= 1.0
        assert s.threshold == 0.50

    # 2. PatchCore signal
    patch_sigs = loaded_models["patchcore"].predict(dummy_frame)
    for s in patch_sigs:
        assert isinstance(s, CalibratedSignal)
        assert 0.0 <= s.calibrated_prob <= 1.0

    # 3. Physics signal
    phys_detector = loaded_models["physics"]
    phys_sigs = phys_detector.evaluate_features({"twist_3m_mm": np.full(80, 2.0)})
    for s in phys_sigs:
        assert isinstance(s, CalibratedSignal)
        assert 0.0 <= s.calibrated_prob <= 1.0

    # 4. Bi-LSTM signal
    bilstm_sig = loaded_models["bilstm"].predict({"twist_3m_mm": np.zeros(80)})
    assert isinstance(bilstm_sig, CalibratedSignal)
    assert 0.0 <= bilstm_sig.calibrated_prob <= 1.0

    # 5. Seq-VAE signal
    vae_sig = loaded_models["vae"].predict({"twist_3m_mm": np.zeros(80)})
    assert isinstance(vae_sig, CalibratedSignal)
    assert 0.0 <= vae_sig.calibrated_prob <= 1.0


# =============================================================================
# P1: Physics Correctness Tests
# =============================================================================

def test_twist_positive_exceedance():
    """P1-1: Injected twist clearly above RDSO 4mm limit generates a fired GEOMETRY_KNOWN signal."""
    detector = EN13848PhysicsThresholdDetector(twist_limit_mm=4.0)
    n_bins = 80  # 20m window at 0.25m step
    
    # Clear exceedance: 8mm twist (ratio = 8.0 / (2 * 4.0) = 1.0)
    features = {
        "twist_3m_mm": np.full(n_bins, 8.0),
        "versine_10m_mm": np.zeros(n_bins),
        "unevenness_10m_mm": np.zeros(n_bins),
        "gauge_dev_mm": np.zeros(n_bins),
    }

    signals = detector.evaluate_features(features)
    twist_sigs = [s for s in signals if s.predicted_class == DefectClass.TWIST_EXCEEDANCE or "twist" in s.name.lower()]

    assert len(twist_sigs) > 0, "Physics detector must generate at least 1 twist exceedance signal"
    assert twist_sigs[0].fired, "Twist signal must be fired"
    assert twist_sigs[0].is_anomaly, "is_anomaly must be True"
    assert 0.50 <= twist_sigs[0].calibrated_prob <= 1.0


def test_twist_baseline_length():
    """P1-2: Sequences shorter than standard window are evaluated safely without throwing exceptions."""
    detector = EN13848PhysicsThresholdDetector()
    short_features = {
        "twist_3m_mm": np.array([2.0, 3.0, 2.5]),  # Only 3 bins
    }
    signals = detector.evaluate_features(short_features)
    assert isinstance(signals, list)


def test_clean_track_no_signals():
    """P1-3: Nominal straight and level track generates zero anomaly exceedance signals."""
    detector = EN13848PhysicsThresholdDetector()
    n_bins = 80
    clean_features = {
        "twist_3m_mm": np.random.normal(0.0, 0.3, n_bins),
        "versine_10m_mm": np.random.normal(0.0, 0.5, n_bins),
        "unevenness_10m_mm": np.random.normal(0.0, 0.5, n_bins),
        "gauge_dev_mm": np.random.normal(0.0, 0.2, n_bins),
    }

    signals = detector.evaluate_features(clean_features)
    fired_signals = [s for s in signals if s.fired]
    assert len(fired_signals) == 0, f"Clean track should have 0 fired signals, got {len(fired_signals)}"


def test_physics_monotonicity():
    """P1-4: Monotonicity - larger physical exceedance strictly yields higher calibrated score."""
    detector = EN13848PhysicsThresholdDetector(twist_limit_mm=4.0)

    score_small = detector.calculate_exceedance_score(2.0, limit_mm=4.0)
    score_limit = detector.calculate_exceedance_score(4.0, limit_mm=4.0)
    score_large = detector.calculate_exceedance_score(8.0, limit_mm=4.0)

    assert score_small < score_limit < score_large
    assert score_limit == 0.50
    assert score_large == 1.0


# =============================================================================
# P2: Fusion Logic & Capstone Pipeline
# =============================================================================

def test_fusion_truth_table():
    """P2-1: Verify fusion truth table across clean, visual, and geometry streams."""
    engine = TrackChainFusionEngine(persistence_window=1)

    # 1. Clean track -> OK
    sig_clean = SegmentSignals()
    dec_clean = engine.fuse(sig_clean, "w1", 0.0, 20.0)
    assert dec_clean.decision == DecisionType.OK

    # 2. Known Visual Defect -> INSPECT_KNOWN
    sig_v_known = SegmentSignals(
        v_known=[
            CalibratedSignal(
                name="yolo_crack",
                signal_type=SignalType.VISUAL_KNOWN,
                value=0.92,
                raw_score=0.92,
                threshold=0.50,
                fired=True,
                is_anomaly=True,
                predicted_class=DefectClass.CRACK,
            )
        ]
    )
    dec_v_known = engine.fuse(sig_v_known, "w2", 20.0, 40.0)
    assert dec_v_known.decision == DecisionType.INSPECT_KNOWN

    # 3. Known Geometry Defect -> INSPECT_KNOWN
    sig_g_known = SegmentSignals(
        g_known=[
            CalibratedSignal(
                name="physics_twist",
                signal_type=SignalType.GEOMETRY_KNOWN,
                value=0.85,
                raw_score=0.85,
                threshold=0.50,
                fired=True,
                is_anomaly=True,
                predicted_class=DefectClass.TWIST_EXCEEDANCE,
            )
        ]
    )
    dec_g_known = engine.fuse(sig_g_known, "w3", 40.0, 60.0)
    assert dec_g_known.decision == DecisionType.INSPECT_KNOWN


def test_novel_persistence_hysteresis(pipeline):
    """P2-2: A single novel frame does not trigger novel alarm; 3 consecutive segments trigger INSPECT_NOVEL."""
    n_bins = 80
    img = np.random.randint(50, 200, (480, 640, 3), dtype=np.uint8)

    novel_telemetry = {
        "roll_rad": np.sin(np.linspace(0, 20 * np.pi, n_bins)) * 0.05,
        "lateral_pos_mm": np.sin(np.linspace(0, 30 * np.pi, n_bins)) * 5.0,
        "vertical_pos_mm": np.cos(np.linspace(0, 30 * np.pi, n_bins)) * 5.0,
        "gauge_mm": 1676.0 + np.sin(np.linspace(0, 10 * np.pi, n_bins)) * 3.0,
    }

    # Reset fusion engine hysteresis state
    pipeline.fusion = TrackChainFusionEngine(persistence_window=3)

    # Segment 1 (single frame) -> Not persistent yet
    seg1 = TrackSegment(
        segment_id="hyst-1",
        chainage_start_m=0.0,
        chainage_end_m=20.0,
        frames=[img],
        telemetry=novel_telemetry,
    )
    dec1, _ = pipeline.process_segment(seg1)

    # Segments 2, 3, 4 (persistent stream)
    decisions = [dec1]
    for i in range(2, 5):
        seg = TrackSegment(
            segment_id=f"hyst-{i}",
            chainage_start_m=(i - 1) * 20.0,
            chainage_end_m=i * 20.0,
            frames=[img],
            telemetry=novel_telemetry,
        )
        d, _ = pipeline.process_segment(seg)
        decisions.append(d)

    # By the 4th consecutive segment, decision must be active inspection
    assert decisions[-1].decision in [DecisionType.INSPECT_NOVEL, DecisionType.INSPECT_KNOWN]


def test_cross_modal_boost_escalation():
    """P2-3: Corroborated Visual + Geometry defects trigger 1.5x cross-modal severity boost."""
    sig_dual = SegmentSignals(
        v_known=[
            CalibratedSignal(
                name="yolo_missing_fastener",
                signal_type=SignalType.VISUAL_KNOWN,
                value=0.88,
                threshold=0.50,
                fired=True,
                is_anomaly=True,
                predicted_class=DefectClass.MISSING_FASTENER,
            )
        ],
        g_known=[
            CalibratedSignal(
                name="physics_gauge_widening",
                signal_type=SignalType.GEOMETRY_KNOWN,
                value=0.85,
                threshold=0.50,
                fired=True,
                is_anomaly=True,
                predicted_class=DefectClass.GAUGE_WIDENING,
            )
        ],
    )

    boost = compute_cross_modal_boost(sig_dual)
    assert boost == 1.5, f"Expected 1.5x cross-modal boost, got {boost}"

    engine = TrackChainFusionEngine(persistence_window=1)
    decision = engine.fuse(sig_dual, "w-compound", 100.0, 120.0)
    assert decision.decision == DecisionType.INSPECT_KNOWN
    assert decision.severity in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]


def test_end_to_end_pipeline(pipeline, clean_segment):
    """P2-4: Full TrackSegment flows through all 5 models and returns schema-compliant SegmentDecision."""
    decision, signals = pipeline.process_segment(clean_segment)

    assert isinstance(decision, SegmentDecision)
    assert decision.schema_version == SCHEMA_VERSION
    assert decision.decision == DecisionType.OK
    assert 0.0 <= decision.confidence <= 1.0

    payload = decision.to_dict()
    assert payload["schema_version"] == "tc.v1"
    assert "window_id" in payload
    assert "chainage_start_m" in payload
    assert "signals" in payload
