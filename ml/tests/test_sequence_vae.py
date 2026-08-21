"""
ml/tests/test_sequence_vae.py
Tests for Phase 2.5: 1D-CNN Sequence VAE for Novel Track Geometry Anomaly Detection.
"""

import pytest
import torch
import numpy as np

from ml.models.geometry.sequence_vae import SequenceVAE, SequenceVAEDetector
from ml.core.schema import SignalType, DefectClass, CalibratedSignal
from ml.data.synthetic_geometry import SyntheticGeometryDataset, GeometryFaultType


def test_sequence_vae_1d_cnn_architecture():
    """Verify 1D-CNN encoder, latent bottleneck (16), decoder transpose, and output shapes."""
    batch_size = 8
    seq_len = 80
    n_features = 5
    latent_dim = 16

    model = SequenceVAE(seq_len=seq_len, n_features=n_features, latent_dim=latent_dim)
    x = torch.randn(batch_size, seq_len, n_features)

    recon_x, mu, logvar = model(x)

    assert recon_x.shape == (batch_size, seq_len, n_features)
    assert mu.shape == (batch_size, latent_dim)
    assert logvar.shape == (batch_size, latent_dim)


def test_sequence_vae_loss_and_beta():
    """Verify Beta-VAE loss function computation (beta=0.01)."""
    model = SequenceVAE(seq_len=80, n_features=5, latent_dim=16)
    x = torch.randn(4, 80, 5)

    recon_x, mu, logvar = model(x)
    total_loss, recon_loss, kld_loss = model.loss_function(recon_x, x, mu, logvar, beta=0.01)

    assert total_loss.item() > 0.0
    assert recon_loss.item() > 0.0
    assert kld_loss.item() >= 0.0
    assert torch.isclose(total_loss, recon_loss + 0.01 * kld_loss, atol=1e-5)


def test_sequence_vae_anomaly_reconstruction_sensitivity():
    """
    Train a tiny Sequence VAE on normal track and verify that it achieves
    much lower reconstruction error on normal test samples than on injected anomalies.
    """
    torch.manual_seed(42)
    model = SequenceVAE(seq_len=80, n_features=5, latent_dim=16)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

    # 1. Synthesize normal sequences
    normal_data = torch.randn(60, 80, 5) * 0.3  # Low amplitude noise

    # Quick train on normal data
    model.train()
    for _ in range(30):
        optimizer.zero_grad()
        recon, mu, logvar = model(normal_data)
        loss, _, _ = model.loss_function(recon, normal_data, mu, logvar, beta=0.01)
        loss.backward()
        optimizer.step()

    # 2. Test error on normal sequence vs extreme harmonic anomaly
    model.eval()
    with torch.no_grad():
        clean_test = torch.randn(1, 80, 5) * 0.3
        err_clean = model.compute_anomaly_score(clean_test).item()

        # Injected anomaly: massive 10mm sine wave across features
        anomalous_test = clean_test.clone()
        x_axis = torch.linspace(0, 20, 80)
        anomalous_test[0, :, 3] += 8.0 * torch.sin(x_axis)
        err_anomaly = model.compute_anomaly_score(anomalous_test).item()

    assert err_anomaly > err_clean * 3.0, f"Expected anomaly error ({err_anomaly}) >> clean error ({err_clean})"


def test_sequence_vae_detector_calibration_and_contract():
    """Verify SequenceVAEDetector predict method and tc.v1 CalibratedSignal compliance."""
    detector = SequenceVAEDetector(weights_path=None)

    # Generate synthetic validation normal data to fit calibration
    normal_windows = np.random.randn(50, 80, 5).astype(np.float32) * 0.5
    thresh = detector.fit_calibration(normal_windows, percentile=95.0)
    assert thresh > 0.0

    # 1. Predict on normal window
    signal_normal = detector.predict(normal_windows[0])
    assert isinstance(signal_normal, CalibratedSignal)
    assert signal_normal.signal_type == SignalType.GEOMETRY_NOVEL
    assert signal_normal.stream_name == "geometry_vae"
    assert 0.0 <= signal_normal.calibrated_prob <= 1.0
    assert signal_normal.raw_score >= 0.0
    assert "reconstruction_error" in signal_normal.explanation

    # 2. Predict on dictionary feature input
    dict_in = {
        "twist_3m_mm": np.zeros(80),
        "versine_10m_mm": np.zeros(80),
        "versine_20m_mm": np.zeros(80),
        "unevenness_10m_mm": np.full(80, 10.0),  # Extreme offset
        "cant_mm": np.zeros(80),
    }
    signal_anomaly = detector.predict(dict_in)
    assert isinstance(signal_anomaly, CalibratedSignal)
    assert signal_anomaly.signal_type == SignalType.GEOMETRY_NOVEL
    assert signal_anomaly.is_anomaly is True
    assert signal_anomaly.predicted_class == DefectClass.GEOMETRY_ANOMALY
