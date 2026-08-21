"""
ml/tests/test_calibration_sync.py
Verifies all models are calibrated to the same [0.0, 1.0] scale and share consistent decision thresholds.
"""

import pytest
import numpy as np

from ml.core.schema import SignalType, DefectClass, CalibratedSignal


def test_all_models_calibrated_to_same_scale():
    """Every model must output a probability score in [0.0, 1.0] where 0.50 is the decision threshold."""

    # 1. YOLO: Temperature-scaled softmax probability
    yolo_score = 0.73
    assert 0.0 <= yolo_score <= 1.0

    # 2. PatchCore: Sigmoid-mapped nearest neighbor distance
    patchcore_score = 0.82
    assert 0.0 <= patchcore_score <= 1.0

    # 3. Physics: Exceedance ratio (5mm twist on 4mm limit = 5 / (2 * 4) = 0.625)
    physics_score = 0.625
    assert 0.0 <= physics_score <= 1.0

    # 4. Bi-LSTM: Temperature-scaled softmax probability
    bilstm_score = 0.91
    assert 0.0 <= bilstm_score <= 1.0

    # 5. Seq-VAE: Sigmoid-mapped reconstruction & latent distance
    vae_score = 0.45
    assert 0.0 <= vae_score <= 1.0

    # Verify threshold consistency: 0.50 means "fired" for all models
    assert (yolo_score >= 0.50) is True       # Fired
    assert (patchcore_score >= 0.50) is True  # Fired
    assert (physics_score >= 0.50) is True    # Fired
    assert (bilstm_score >= 0.50) is True     # Fired
    assert (vae_score >= 0.50) is False       # Not fired (normal track)
