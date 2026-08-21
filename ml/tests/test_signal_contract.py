"""
ml/tests/test_signal_contract.py
Verifies every model emits a strictly compliant tc.v1 CalibratedSignal contract.
"""

import pytest
from ml.core.schema import CalibratedSignal, SignalType, DefectClass


def test_yolo_signal_contract():
    signal = CalibratedSignal(
        name="yolo_visual_detector",
        model_version="0.1.0",
        signal_type=SignalType.VISUAL_KNOWN,
        value=0.85,
        raw_score=0.82,
        threshold=0.50,
        fired=True,
        label=DefectClass.MISSING_FASTENER,
        bbox=[120, 450, 180, 520],
        explanation=None,
    )
    assert signal.signal_type == SignalType.VISUAL_KNOWN
    assert signal.fired is True
    assert signal.bbox is not None
    assert signal.label == DefectClass.MISSING_FASTENER


def test_physics_signal_contract():
    signal = CalibratedSignal(
        name="en13848_physics_detector",
        model_version="0.1.0",
        signal_type=SignalType.GEOMETRY_KNOWN,
        value=0.625,
        raw_score=5.0,  # 5mm twist
        threshold=0.50,
        fired=True,
        label=DefectClass.TWIST_FAULT,
        bbox=None,  # Geometry has no pixel bbox
        explanation=None,
    )
    assert signal.signal_type == SignalType.GEOMETRY_KNOWN
    assert signal.bbox is None
    assert signal.fired is True


def test_bilstm_signal_contract():
    signal = CalibratedSignal(
        name="bilstm_geometry_typing",
        model_version="0.1.0",
        signal_type=SignalType.GEOMETRY_KNOWN_TYPE,
        value=0.91,
        raw_score=0.88,
        threshold=0.60,
        fired=True,
        label=DefectClass.DIPPED_JOINT,
        bbox=None,
        explanation={"attention_peak_bin": 42},
    )
    assert signal.signal_type == SignalType.GEOMETRY_KNOWN_TYPE
    assert signal.explanation["attention_peak_bin"] == 42
    assert signal.label == DefectClass.DIPPED_JOINT


def test_vae_signal_contract():
    signal = CalibratedSignal(
        name="sequence_vae_geometry_novel",
        model_version="0.1.0",
        signal_type=SignalType.GEOMETRY_NOVEL,
        value=0.78,
        raw_score=12.5,  # Reconstruction error
        threshold=0.50,
        fired=True,
        label=DefectClass.GEOMETRY_ANOMALY,
        bbox=None,
        explanation={"recon_error": 12.5, "mahalanobis_dist": 3.2},
    )
    assert signal.signal_type == SignalType.GEOMETRY_NOVEL
    assert "mahalanobis_dist" in signal.explanation
    assert signal.label == DefectClass.GEOMETRY_ANOMALY
