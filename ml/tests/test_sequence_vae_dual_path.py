"""
ml/tests/test_sequence_vae_dual_path.py
Validates Dual-Path Anomaly Scoring (Reconstruction MSE + Latent Mahalanobis Distance).
"""

import pytest
import numpy as np
import torch

from ml.models.geometry.sequence_vae import SequenceVAE, SequenceVAEDetector
from ml.core.schema import SignalType, DefectClass, CalibratedSignal


def test_dual_path_latent_distribution_fitting():
    """Verify that fitting latent distribution computes baseline mean and inverse covariance."""
    detector = SequenceVAEDetector(alpha=0.7)

    # 40 normal sequences of 80 bins x 5 features
    normal_seqs = np.random.randn(40, 80, 5).astype(np.float32) * 0.2
    detector.fit_latent_distribution(normal_seqs)

    assert detector.normal_latent_mean is not None
    assert detector.normal_latent_cov_inv is not None
    assert detector.normal_latent_mean.shape == (detector.latent_dim,)
    assert detector.normal_latent_cov_inv.shape == (detector.latent_dim, detector.latent_dim)


def test_dual_path_scoring_combination():
    """Verify that anomaly score correctly weights reconstruction and Mahalanobis components."""
    detector = SequenceVAEDetector(alpha=0.7)

    normal_seqs = np.random.randn(50, 80, 5).astype(np.float32) * 0.1
    detector.fit_latent_distribution(normal_seqs)

    test_seq = np.random.randn(80, 5).astype(np.float32) * 0.1
    score = detector.compute_anomaly_score(test_seq)

    assert isinstance(score, float)
    assert score >= 0.0

    # Extreme anomaly (high MSE and high latent shift)
    anom_seq = np.full((80, 5), 15.0, dtype=np.float32)
    anom_score = detector.compute_anomaly_score(anom_seq)

    assert anom_score > score * 5.0, f"Expected anomaly score {anom_score} >> normal score {score}"
