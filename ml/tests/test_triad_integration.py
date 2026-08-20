# Integration test for the Core Sensor Fusion Triad: YOLO (2.1), PatchCore (2.2), Physics (2.3) (tc.v1 SOTA).

import pytest
import numpy as np
from PIL import Image, ImageDraw

from ml.core.schema import (
    ChainageWindow,
    SegmentDecision,
    CalibratedSignal,
    SignalType,
    DefectClass,
    DecisionType,
)
from ml.models.vision.detector import YOLOv8DefectDetector
from ml.models.vision.anomaly import PatchCoreAnomalyDetector
from ml.features.en13848 import EN13848PhysicsCalculator
from ml.models.geometry.physics_detector import EN13848PhysicsThresholdDetector
from ml.fusion.rules import PersistenceRuleFusion
from ml.inference.pipeline import EndToEndInferencePipeline


def create_synthetic_track_frame(defect_type: str = "none") -> np.ndarray:
    """Create a synthetic 640x640 railway track image for testing."""
    img = Image.new("RGB", (640, 640), color=(70, 75, 80))
    draw = ImageDraw.Draw(img)
    # Rails
    draw.line([(180, 0), (180, 640)], fill=(180, 190, 200), width=16)
    draw.line([(460, 0), (460, 640)], fill=(180, 190, 200), width=16)
    # Sleepers
    for y in range(40, 640, 80):
        draw.rectangle([60, y, 580, y + 30], fill=(40, 30, 20))
        draw.rectangle([155, y + 5, 175, y + 25], fill=(120, 130, 140))
        draw.rectangle([465, y + 5, 485, y + 25], fill=(120, 130, 140))

    if defect_type == "novel_anomaly":
        # Draw irregular oil stain anomaly
        draw.ellipse([260, 260, 380, 380], fill=(20, 15, 10))

    return np.array(img)


def test_triad_synchronized_processing_and_fusion(monkeypatch):
    """
    Test that a single TrackSegment containing both a visual defect and a geometry twist
    is processed synchronously through all 3 models, calibrated to [0,1], and fused.
    """
    # 1. Instantiate the Triad models
    yolo = YOLOv8DefectDetector(weights_path="")
    # Mock YOLO to simulate detecting a missing fastener
    def mock_yolo_predict(frame: np.ndarray):
        return [
            CalibratedSignal(
                stream_name="vision_detector",
                raw_score=0.92,
                calibrated_prob=0.92,
                predicted_class=DefectClass.MISSING_FASTENER,
                is_anomaly=True,
                signal_type=SignalType.VISUAL_KNOWN,
                threshold=0.50,
                bbox=(150.0, 120.0, 180.0, 150.0),
                explanation="Missing fastener clip detected",
            )
        ]
    monkeypatch.setattr(yolo, "predict", mock_yolo_predict)

    patchcore = PatchCoreAnomalyDetector()
    phys_calc = EN13848PhysicsCalculator(nominal_gauge_mm=1676.0)
    phys_detector = EN13848PhysicsThresholdDetector(twist_limit_mm=4.0)
    fusion = PersistenceRuleFusion(persistence_window=1, known_threshold=0.60)

    pipeline = EndToEndInferencePipeline(
        yolo_detector=yolo,
        patchcore_detector=patchcore,
        physics_calculator=phys_calc,
        physics_detector=phys_detector,
        fusion_engine=fusion,
    )

    # 2. Build synthetic ChainageWindow (100.0m to 125.0m, 100 samples of 0.25m)
    n_samples = 100
    distances = np.linspace(100.0, 125.0, n_samples)
    timestamps = np.linspace(0.0, 2.5, n_samples)

    # Inject 5.0mm twist into roll telemetry
    # Cant = G * sin(roll) -> 5.0mm cant step
    roll_arr = np.zeros(n_samples)
    roll_arr[20:] = np.arcsin(5.0 / 1676.0)

    raw_telemetry = {
        "roll_rad": roll_arr,
        "gauge_mm": np.full(n_samples, 1676.0),
        "lateral_pos_mm": np.zeros(n_samples),
        "vertical_pos_mm": np.zeros(n_samples),
    }
    frame = create_synthetic_track_frame()

    window = ChainageWindow(
        start_chainage_m=100.0,
        end_chainage_m=125.0,
        timestamps=timestamps,
        distances=distances,
        raw_telemetry=raw_telemetry,
        frames=[frame],
    )

    # 3. Process window through Triad pipeline
    decision = pipeline.process_window(window)

    # 4. Verify Decision & Multi-Modal Signals
    assert isinstance(decision, SegmentDecision)
    assert decision.decision == DecisionType.INSPECT_KNOWN
    assert decision.start_chainage_m == 100.0
    assert decision.end_chainage_m == 125.0

    # Verify both streams fired
    signal_types = [s.signal_type for s in decision.signals]
    assert SignalType.VISUAL_KNOWN in signal_types
    assert SignalType.GEOMETRY_KNOWN in signal_types

    # Verify physics twist signal exceedance math (5.0mm vs 4.0mm limit -> 5.0 / (2 * 4.0) = 0.625)
    twist_sig = next(s for s in decision.signals if s.predicted_class == DefectClass.TWIST_EXCEEDANCE)
    assert twist_sig.is_anomaly is True
    assert np.isclose(twist_sig.calibrated_prob, 0.625)

    # Verify YOLO signal
    yolo_sig = next(s for s in decision.signals if s.predicted_class == DefectClass.MISSING_FASTENER)
    assert yolo_sig.is_anomaly is True
    assert yolo_sig.bbox is not None


def test_triad_novel_anomaly_decision(monkeypatch):
    """Test that a novel surface anomaly triggers INSPECT_NOVEL when geometry is clean."""
    yolo = YOLOv8DefectDetector(weights_path="")
    monkeypatch.setattr(yolo, "predict", lambda frame: [])  # YOLO is silent

    patchcore = PatchCoreAnomalyDetector()
    # Mock PatchCore to fire an anomaly signal
    def mock_patch_predict(frame: np.ndarray):
        return [
            CalibratedSignal(
                stream_name="patchcore_anomaly",
                raw_score=14.2,
                calibrated_prob=0.88,
                predicted_class=DefectClass.VISUAL_ANOMALY,
                is_anomaly=True,
                signal_type=SignalType.VISUAL_NOVEL,
                threshold=0.50,
                bbox=(260.0, 260.0, 380.0, 380.0),
                explanation="Novel visual anomaly detected",
            )
        ]
    monkeypatch.setattr(patchcore, "predict", mock_patch_predict)

    fusion = PersistenceRuleFusion(persistence_window=1, novel_threshold=0.65)
    pipeline = EndToEndInferencePipeline(
        yolo_detector=yolo,
        patchcore_detector=patchcore,
        fusion_engine=fusion,
    )

    n_samples = 50
    window = ChainageWindow(
        start_chainage_m=200.0,
        end_chainage_m=212.5,
        timestamps=np.linspace(0.0, 1.0, n_samples),
        distances=np.linspace(200.0, 212.5, n_samples),
        raw_telemetry={"gauge_mm": np.full(n_samples, 1676.0), "roll_rad": np.zeros(n_samples)},
        frames=[create_synthetic_track_frame("novel_anomaly")],
    )

    decision = pipeline.process_window(window)
    assert decision.decision == DecisionType.INSPECT_NOVEL
    assert decision.confidence == 0.88
    assert len(decision.signals) >= 1
    assert decision.signals[0].signal_type == SignalType.VISUAL_NOVEL


def test_triad_normal_track_ok_decision():
    """Test that perfectly normal track produces an OK decision."""
    pipeline = EndToEndInferencePipeline()
    n_samples = 50
    window = ChainageWindow(
        start_chainage_m=0.0,
        end_chainage_m=12.5,
        timestamps=np.linspace(0.0, 1.0, n_samples),
        distances=np.linspace(0.0, 12.5, n_samples),
        raw_telemetry={"gauge_mm": np.full(n_samples, 1676.0), "roll_rad": np.zeros(n_samples)},
        frames=[],
    )

    decision = pipeline.process_window(window)
    assert decision.decision == DecisionType.OK
    assert decision.confidence >= 0.90
