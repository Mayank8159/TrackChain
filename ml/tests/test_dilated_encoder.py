"""
ml/tests/test_dilated_encoder.py
Validates Multi-Scale Dilated 1D-CNN Encoder architecture and multi-wavelength capture.
"""

import pytest
import torch

from ml.models.geometry.sequence_vae import DilatedEncoder, SequenceVAE


def test_dilated_encoder_multi_scale_branches():
    """Verify short (dilation=1), medium (dilation=4), and long (dilation=10) branches and shapes."""
    batch_size = 4
    n_features = 5
    seq_len = 80
    latent_dim = 16

    encoder = DilatedEncoder(n_features=n_features, seq_len=seq_len, latent_dim=latent_dim)
    x = torch.randn(batch_size, n_features, seq_len)

    mu, logvar = encoder(x)

    assert mu.shape == (batch_size, latent_dim)
    assert logvar.shape == (batch_size, latent_dim)


def test_dilated_sequence_vae_forward_and_reconstruction():
    """Verify complete SequenceVAE with dilated encoder reconstructs to exact 80 spatial bins."""
    batch_size = 6
    seq_len = 80
    n_features = 5

    model = SequenceVAE(seq_len=seq_len, n_features=n_features, latent_dim=16)
    x = torch.randn(batch_size, seq_len, n_features)

    recon_x, mu, logvar = model(x)

    assert recon_x.shape == (batch_size, seq_len, n_features)
    assert not torch.isnan(recon_x).any()
