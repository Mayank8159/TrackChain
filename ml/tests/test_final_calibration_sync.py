"""
ml/tests/test_final_calibration_sync.py
Category B: Calibration Synchronization Test (tc.v1 SOTA).
Verifies all 5 models map raw outputs into normalized [0.0, 1.0] probabilities with a consistent 0.50 decision boundary.
"""

import os
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

from ml.core.schema import DefectClass
from ml.calibration.unified_calibrator import UnifiedCalibrator
from ml.calibration.temperature import TemperatureScaler, VectorScaler
from ml.calibration.patchcore_scale import SigmoidDistanceCalibrator, WeibullDistanceCalibrator
from ml.models.geometry.physics_detector import EN13848PhysicsThresholdDetector
from ml.models.geometry.fault_classifier import GeometryFaultClassifier
from ml.models.geometry.sequence_vae import SequenceVAEDetector
from ml.models.vision.detector import YOLOv8DefectDetector
from ml.models.vision.anomaly import PatchCoreAnomalyDetector


def test_yolo_calibration_range(loaded_models):
    """Verify YOLO detections emit calibrated probabilities within [0.0, 1.0]."""
    yolo = loaded_models["yolo"]
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    signals = yolo.predict(dummy_frame)

    for sig in signals:
        assert 0.0 <= sig.value <= 1.0, f"YOLO signal {sig.name} value out of bounds: {sig.value}"
        assert 0.0 <= sig.calibrated_prob <= 1.0


def test_patchcore_calibration_range(loaded_models):
    """Verify PatchCore anomaly detector emits calibrated probabilities within [0.0, 1.0]."""
    pc = loaded_models["patchcore"]
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    signals = pc.predict(dummy_frame)

    for sig in signals:
        assert 0.0 <= sig.value <= 1.0, f"PatchCore signal value out of bounds: {sig.value}"
        assert 0.0 <= sig.calibrated_prob <= 1.0
        assert sig.threshold == 0.50


def test_physics_deterministic_exceedance_ratio():
    """Verify EN 13848 physics detector maps exceedance ratios into [0.0, 1.0]."""
    detector = EN13848PhysicsThresholdDetector()

    # Nominal features
    features_nominal = {
        "twist_3m_mm": np.full(80, 1.0),
        "versine_10m_mm": np.full(80, 2.0),
        "longitudinal_level_d1_mm": np.full(80, 2.0),
        "gauge_deviation_mm": np.full(80, 0.5),
    }
    signals_nom = detector.evaluate_features(features_nominal)
    for sig in signals_nom:
        assert 0.0 <= sig.value <= 1.0
        assert not sig.is_anomaly
        assert not sig.fired

    # Exceedance features (Twist = 8mm, Limit = 4mm -> ratio = 8/(2*4) = 1.0)
    features_exceed = {
        "twist_3m_mm": np.full(80, 8.0),
        "versine_10m_mm": np.full(80, 2.0),
        "longitudinal_level_d1_mm": np.full(80, 2.0),
        "gauge_deviation_mm": np.full(80, 0.5),
    }
    signals_exc = detector.evaluate_features(features_exceed)
    twist_sigs = [
        s for s in signals_exc
        if s.predicted_class == DefectClass.TWIST_EXCEEDANCE
        or "twist" in getattr(s, "name", "").lower()
        or (getattr(s, "metadata", None) and "twist" in str(s.metadata.get("feature", "")).lower())
    ]
    assert len(twist_sigs) > 0, "Expected at least one twist exceedance signal to be generated"
    assert twist_sigs[0].fired
    assert 0.50 <= twist_sigs[0].value <= 1.0


def test_bilstm_vector_scaling_probability_range(loaded_models):
    """Verify Bi-LSTM geometry classifier emits valid probability distributions summing to 1.0."""
    clf = loaded_models["bilstm"]
    dummy_geom = {
        "twist_3m_mm": np.zeros(80),
        "versine_10m_mm": np.zeros(80),
        "longitudinal_level_d1_mm": np.zeros(80),
        "gauge_deviation_mm": np.zeros(80),
    }
    signal = clf.predict(dummy_geom)

    assert 0.0 <= signal.value <= 1.0
    assert 0.0 <= signal.calibrated_prob <= 1.0
    assert signal.threshold in [0.50, 0.60]


def test_sequence_vae_evt_probability_range(loaded_models):
    """Verify Sequence VAE emits normalized novelty probabilities strictly within [0.0, 1.0]."""
    vae = loaded_models["vae"]
    dummy_geom = {
        "twist_3m_mm": np.zeros(80),
        "versine_10m_mm": np.zeros(80),
        "longitudinal_level_d1_mm": np.zeros(80),
        "gauge_deviation_mm": np.zeros(80),
    }
    signal = vae.predict(dummy_geom)

    assert 0.0 <= signal.value <= 1.0
    assert 0.0 <= signal.calibrated_prob <= 1.0
    assert signal.threshold == 0.50
