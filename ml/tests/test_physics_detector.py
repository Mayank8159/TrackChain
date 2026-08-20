# Unit tests for deterministic EN 13848 / RDSO physics threshold detector (tc.v1 SOTA).

import pytest
import numpy as np
from ml.models.geometry.physics_detector import EN13848PhysicsThresholdDetector
from ml.core.schema import DefectClass, SignalType, CalibratedSignal


def test_physics_detector_initialization():
    detector = EN13848PhysicsThresholdDetector()
    assert detector.limits["twist_3m"] == 4.0
    assert detector.limits["versine_10m"] == 6.0
    assert detector.limits["unevenness_10m"] == 6.0
    assert detector.operating_threshold == 0.50


def test_physics_detector_exceedance_calibration():
    detector = EN13848PhysicsThresholdDetector(twist_limit_mm=4.0)
    
    # Measured = 0mm -> Score = 0.0
    assert detector.calculate_exceedance_score(0.0, 4.0) == 0.0

    # Measured = Limit (4.0mm) -> Score = 0.50 (Exactly at threshold)
    assert detector.calculate_exceedance_score(4.0, 4.0) == 0.50

    # Measured = 5.0mm -> Score = 5.0 / (2 * 4.0) = 0.625
    assert np.isclose(detector.calculate_exceedance_score(5.0, 4.0), 0.625)

    # Measured = 8.0mm (2x Limit) -> Score = 1.0
    assert detector.calculate_exceedance_score(8.0, 4.0) == 1.0

    # Measured = 12.0mm (>2x Limit) -> Capped at 1.0
    assert detector.calculate_exceedance_score(12.0, 4.0) == 1.0


def test_physics_detector_twist_alarm():
    detector = EN13848PhysicsThresholdDetector(twist_limit_mm=4.0)

    # Synthetic track segment with a 5.0mm twist fault
    features = {
        "twist_3m_mm": np.array([0.0, 1.2, 5.0, 2.0, 0.0]),
        "gauge_dev_mm": np.zeros(5),
    }

    signals = detector.evaluate_features(features)
    assert len(signals) >= 1

    twist_sig = next(s for s in signals if s.predicted_class == DefectClass.TWIST_EXCEEDANCE)
    assert isinstance(twist_sig, CalibratedSignal)
    assert twist_sig.signal_type == SignalType.GEOMETRY_KNOWN
    assert twist_sig.is_anomaly is True
    assert twist_sig.raw_score == 5.0
    assert np.isclose(twist_sig.calibrated_prob, 0.625)
    assert twist_sig.metadata["severity"] == "critical"


def test_physics_detector_gauge_widening_and_tightening():
    detector = EN13848PhysicsThresholdDetector(gauge_limit_mm=6.0)

    # 1. Gauge Widening (+7.0mm)
    wide_signals = detector.evaluate_features({"gauge_dev_mm": np.array([0.0, 7.0, 0.0])})
    wide_sig = next(s for s in wide_signals if s.predicted_class == DefectClass.GAUGE_WIDENING)
    assert wide_sig.is_anomaly is True
    assert wide_sig.raw_score == 7.0
    assert wide_sig.calibrated_prob > 0.50
    assert wide_sig.metadata["deviation_type"] == "widening"

    # 2. Gauge Tightening (-7.0mm)
    tight_signals = detector.evaluate_features({"gauge_dev_mm": np.array([0.0, -7.0, 0.0])})
    tight_sig = next(s for s in tight_signals if s.predicted_class == DefectClass.GAUGE_WIDENING)
    assert tight_sig.is_anomaly is True
    assert tight_sig.raw_score == 7.0
    assert tight_sig.metadata["deviation_type"] == "tightening"


def test_physics_detector_no_alarm_on_normal_track():
    detector = EN13848PhysicsThresholdDetector()

    features = {
        "twist_3m_mm": np.full(50, 0.5),      # 0.5mm vs 4.0mm limit (Score: 0.06)
        "gauge_dev_mm": np.full(50, 1.0),     # 1.0mm vs 6.0mm limit (Score: 0.08)
        "versine_10m_mm": np.full(50, 0.8),   # 0.8mm vs 6.0mm limit (Score: 0.06)
        "unevenness_10m_mm": np.full(50, 0.6),# 0.6mm vs 6.0mm limit (Score: 0.05)
    }

    signals = detector.evaluate_features(features)
    fired_signals = [s for s in signals if s.is_anomaly]
    assert len(fired_signals) == 0
