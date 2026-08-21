"""
ml/tests/test_pipeline_integration.py
End-to-End Master Pipeline Integration Tests (tc.v1 SOTA).
Validates all 5 models (YOLOv8, PatchCore, Physics, Bi-LSTM, Sequence VAE) and Persistence Rule Fusion.
"""

import pytest
import numpy as np
from PIL import Image, ImageDraw

from ml.core.schema import (
    TrackSegment,
    ChainageWindow,
    SegmentDecision,
    SegmentSignals,
    DecisionType,
    Decision,
    DefectClass,
    SignalType,
    DefectFamily,
    SeverityLevel,
    Severity,
    CalibratedSignal,
)
from ml.models.vision.detector import YOLOv8DefectDetector
from ml.models.vision.anomaly import PatchCoreAnomalyDetector
from ml.features.en13848 import EN13848PhysicsCalculator
from ml.models.geometry.physics_detector import EN13848PhysicsThresholdDetector
from ml.models.geometry.fault_classifier import GeometryFaultClassifier
from ml.models.geometry.sequence_vae import SequenceVAEDetector
from ml.fusion.rules import TrackChainFusionEngine
from ml.inference.pipeline import TrackChainMLPipeline


def create_test_frame(color=(60, 60, 60)) -> np.ndarray:
    img = Image.new("RGB", (640, 640), color=color)
    return np.array(img)


def test_master_pipeline_normal_track_flow():
    """Verify that a perfectly clean track segment evaluates to OK with low severity."""
    pipeline = TrackChainMLPipeline(conditional_typing=True)

    n_samples = 80
    segment = TrackSegment(
        segment_id="seg-00100",
        chainage_start_m=100.0,
        chainage_end_m=120.0,
        frames=[create_test_frame()],
        telemetry={
            "roll_rad": np.zeros(n_samples),
            "gauge_mm": np.full(n_samples, 1676.0),
            "lateral_pos_mm": np.zeros(n_samples),
            "vertical_pos_mm": np.zeros(n_samples),
        },
    )

    decision, signals = pipeline.process_segment(segment)

    assert isinstance(decision, SegmentDecision)
    assert decision.decision == DecisionType.OK
    assert decision.severity == SeverityLevel.NORMAL
    assert decision.confidence >= 0.90
    # Bi-LSTM was skipped conditionally
    assert len(signals.g_type) == 0


def test_master_pipeline_known_visual_defect(monkeypatch):
    """Verify that YOLO missing fastener triggers immediate INSPECT_KNOWN."""
    pipeline = TrackChainMLPipeline()

    # Mock YOLO to simulate missing fastener
    def mock_yolo_predict(frame: np.ndarray):
        return [
            CalibratedSignal(
                stream_name="vision_detector",
                raw_score=0.94,
                calibrated_prob=0.94,
                predicted_class=DefectClass.MISSING_FASTENER,
                is_anomaly=True,
                signal_type=SignalType.VISUAL_KNOWN,
                threshold=0.50,
                bbox=(100.0, 100.0, 150.0, 150.0),
            )
        ]
    monkeypatch.setattr(pipeline.yolo, "predict", mock_yolo_predict)

    n_samples = 80
    segment = TrackSegment(
        segment_id="seg-00200",
        chainage_start_m=200.0,
        chainage_end_m=220.0,
        frames=[create_test_frame()],
        telemetry={"gauge_mm": np.full(n_samples, 1676.0), "roll_rad": np.zeros(n_samples)},
    )

    decision, signals = pipeline.process_segment(segment)

    assert decision.decision == DecisionType.INSPECT_KNOWN
    assert decision.defect_family == DefectFamily.VISUAL_COMPONENT
    assert decision.primary_fault == DefectClass.MISSING_FASTENER
    assert decision.severity in (SeverityLevel.HIGH, SeverityLevel.CRITICAL)


def test_master_pipeline_geometry_physics_and_bilstm_typing():
    """Verify that Physics limit exceedance triggers conditional Bi-LSTM typing and INSPECT_KNOWN."""
    pipeline = TrackChainMLPipeline(conditional_typing=True)

    n_samples = 80
    roll_with_twist = np.zeros(n_samples)
    roll_with_twist[30:] = np.arcsin(5.0 / 1676.0)  # 5mm twist breach

    segment = TrackSegment(
        segment_id="seg-00300",
        chainage_start_m=300.0,
        chainage_end_m=320.0,
        frames=[],
        telemetry={
            "roll_rad": roll_with_twist,
            "gauge_mm": np.full(n_samples, 1676.0),
            "lateral_pos_mm": np.zeros(n_samples),
            "vertical_pos_mm": np.zeros(n_samples),
        },
    )

    decision, signals = pipeline.process_segment(segment)

    assert decision.decision == DecisionType.INSPECT_KNOWN
    assert decision.defect_family == DefectFamily.GEOMETRY
    # Bi-LSTM was conditionally triggered
    assert len(signals.g_type) == 1
    assert signals.g_type[0].signal_type == SignalType.GEOMETRY_KNOWN_TYPE


def test_master_pipeline_temporal_persistence_novel_anomaly(monkeypatch):
    """
    Verify that a novel anomaly requires 3 consecutive persistent windows to trigger INSPECT_NOVEL.
    A single isolated spike is suppressed (filtering transient noise).
    """
    fusion = TrackChainFusionEngine(persistence_window=3)
    pipeline = TrackChainMLPipeline(fusion_engine=fusion)

    # Mock Sequence VAE to fire an anomaly
    def mock_vae_predict(features):
        return CalibratedSignal(
            stream_name="geometry_vae",
            raw_score=4.5,
            calibrated_prob=0.85,
            predicted_class=DefectClass.GEOMETRY_ANOMALY,
            is_anomaly=True,
            signal_type=SignalType.GEOMETRY_NOVEL,
            threshold=0.50,
        )
    monkeypatch.setattr(pipeline.sequence_vae, "predict", mock_vae_predict)

    n_samples = 80
    base_segment = TrackSegment(
        segment_id="seg-00400",
        chainage_start_m=400.0,
        chainage_end_m=420.0,
        frames=[],
        telemetry={"gauge_mm": np.full(n_samples, 1676.0), "roll_rad": np.zeros(n_samples)},
    )

    # Window 1: Anomaly occurs once -> suppressed by persistence
    dec_1, _ = pipeline.process_segment(base_segment)
    assert dec_1.decision == DecisionType.OK

    # Window 2: Anomaly occurs twice -> still waiting for 3rd confirmation
    dec_2, _ = pipeline.process_segment(base_segment)
    assert dec_2.decision == DecisionType.OK

    # Window 3: Anomaly persisted for 3 consecutive windows -> CONFIRMED INSPECT_NOVEL
    dec_3, _ = pipeline.process_segment(base_segment)
    assert dec_3.decision == DecisionType.INSPECT_NOVEL
    assert dec_3.defect_family == DefectFamily.NOVEL_ANOMALY
    assert dec_3.primary_fault == DefectClass.GEOMETRY_ANOMALY
