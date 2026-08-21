"""
ml/tests/conftest.py
Shared test fixtures for the TrackChain Phase 2.7 Verification Suite (tc.v1 SOTA).
Provides session-scoped loaded models, fusion engine, and synthetic test segments.
"""

import sys
from pathlib import Path
import pytest
import numpy as np
import yaml
from PIL import Image

# Ensure repo root is in sys.path
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from ml.core.schema import TrackSegment, ChainageWindow
from ml.models.vision.detector import YOLOv8DefectDetector
from ml.models.vision.anomaly import PatchCoreAnomalyDetector
from ml.models.geometry.physics_detector import EN13848PhysicsThresholdDetector
from ml.models.geometry.fault_classifier import GeometryFaultClassifier
from ml.models.geometry.sequence_vae import SequenceVAEDetector
from ml.fusion.rules import TrackChainFusionEngine
from ml.inference.pipeline import TrackChainMLPipeline


@pytest.fixture(scope="session")
def test_config():
    """Load test configuration YAML."""
    cfg_path = repo_root / "ml" / "configs" / "test.yaml"
    if cfg_path.exists():
        with open(cfg_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {
        "test": {
            "latency_budget_ms": {"full_pipeline_fp32": 60, "full_pipeline_int8": 35},
            "fusion": {"persistence_window": 3, "decision_threshold": 0.5},
            "calibration": {"score_min": 0.0, "score_max": 1.0},
        }
    }


@pytest.fixture(scope="session")
def loaded_models():
    """Load all 5 models once per test session for fast test execution."""
    yolo = YOLOv8DefectDetector()
    patchcore = PatchCoreAnomalyDetector()
    physics = EN13848PhysicsThresholdDetector()
    bilstm = GeometryFaultClassifier(weights_path=None)
    vae = SequenceVAEDetector(weights_path=None, calibrator_path=None)

    return {
        "yolo": yolo,
        "patchcore": patchcore,
        "physics": physics,
        "bilstm": bilstm,
        "vae": vae,
    }


@pytest.fixture(scope="session")
def fusion_engine():
    """Configured TrackChainFusionEngine fixture."""
    return TrackChainFusionEngine(persistence_window=3, known_threshold=0.60, novel_threshold=0.50)


@pytest.fixture(scope="session")
def pipeline(loaded_models, fusion_engine):
    """Full TrackChainMLPipeline initialized with session-scoped models."""
    return TrackChainMLPipeline(
        yolo_detector=loaded_models["yolo"],
        patchcore_detector=loaded_models["patchcore"],
        physics_detector=loaded_models["physics"],
        fault_classifier=loaded_models["bilstm"],
        sequence_vae=loaded_models["vae"],
        fusion_engine=fusion_engine,
        conditional_typing=False,
    )


@pytest.fixture
def clean_segment():
    """Nominal TrackSegment with clean rail frame and nominal geometry telemetry."""
    n_bins = 80  # 20m window at 0.25m
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[200:280, :] = 120  # Nominal rail band

    telemetry = {
        "roll_rad": np.zeros(n_bins),
        "lateral_pos_mm": np.random.normal(0.0, 0.2, n_bins),
        "vertical_pos_mm": np.random.normal(0.0, 0.2, n_bins),
        "gauge_mm": np.full(n_bins, 1676.0),
    }

    return TrackSegment(
        segment_id="seg-clean-001",
        chainage_start_m=0.0,
        chainage_end_m=20.0,
        frames=[img],
        telemetry=telemetry,
        section_type="mainline_standard",
    )


@pytest.fixture
def defective_segment():
    """TrackSegment with injected twist exceedance and visual defect simulation."""
    n_bins = 80
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[200:280, :] = 120
    # Injected visual anomaly mark
    img[220:260, 300:340] = 255

    # Twist exceedance > 4mm
    vertical = np.zeros(n_bins)
    vertical[35:45] = 12.0  # Dip causing twist exceedance

    telemetry = {
        "roll_rad": np.zeros(n_bins),
        "lateral_pos_mm": np.random.normal(0.0, 0.2, n_bins),
        "vertical_pos_mm": vertical,
        "gauge_mm": np.full(n_bins, 1676.0),
    }

    return TrackSegment(
        segment_id="seg-defect-001",
        chainage_start_m=100.0,
        chainage_end_m=120.0,
        frames=[img],
        telemetry=telemetry,
        section_type="mainline_standard",
    )


@pytest.fixture
def novel_segment():
    """TrackSegment with high-frequency novel perturbation in geometry and novel visual pattern."""
    n_bins = 80
    img = np.random.randint(50, 200, (480, 640, 3), dtype=np.uint8)

    # High frequency novel pattern in geometry
    telemetry = {
        "roll_rad": np.sin(np.linspace(0, 20 * np.pi, n_bins)) * 0.05,
        "lateral_pos_mm": np.sin(np.linspace(0, 30 * np.pi, n_bins)) * 5.0,
        "vertical_pos_mm": np.cos(np.linspace(0, 30 * np.pi, n_bins)) * 5.0,
        "gauge_mm": 1676.0 + np.sin(np.linspace(0, 10 * np.pi, n_bins)) * 3.0,
    }

    return TrackSegment(
        segment_id="seg-novel-001",
        chainage_start_m=200.0,
        chainage_end_m=220.0,
        frames=[img],
        telemetry=telemetry,
        section_type="mainline_standard",
    )


@pytest.fixture
def sample_track_segment(clean_segment):
    """Alias for standard track segment."""
    return clean_segment
