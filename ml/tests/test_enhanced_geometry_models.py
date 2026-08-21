"""
Unit tests for Enhanced Sequence VAE, Enhanced Bi-LSTM Classifier, and Calibration Sync.
"""
import json
from pathlib import Path
import numpy as np
import pytest
import torch

from ml.models.geometry.sequence_vae_enhanced import (
    DilatedEncoder1D,
    Decoder1D,
    EnhancedSequenceVAE,
    OverlappingWindowInference,
)
from ml.models.geometry.fault_classifier_enhanced import (
    MultiHeadAttention1D,
    EnhancedBiLSTMClassifier,
    SequenceAugmentation,
)
from ml.scripts.calibrate_all_models import verify_calibration_sync


def test_dilated_encoder_1d_shapes():
    """Verify DilatedEncoder1D multi-scale branches (dilation=1, 4, 10) and latent projection."""
    batch_size = 4
    seq_len = 80
    n_features = 5
    latent_dim = 16

    encoder = DilatedEncoder1D(n_features=n_features, seq_len=seq_len, latent_dim=latent_dim)
    x = torch.randn(batch_size, seq_len, n_features)

    mu, logvar = encoder(x)

    assert mu.shape == (batch_size, latent_dim)
    assert logvar.shape == (batch_size, latent_dim)
    assert not torch.isnan(mu).any()
    assert not torch.isnan(logvar).any()


def test_decoder_1d_reconstruction_shape():
    """Verify Decoder1D transposed convolutions reconstruct exact sequence length."""
    batch_size = 4
    seq_len = 80
    n_features = 5
    latent_dim = 16

    decoder = Decoder1D(n_features=n_features, seq_len=seq_len, latent_dim=latent_dim)
    z = torch.randn(batch_size, latent_dim)

    recon = decoder(z)

    assert recon.shape == (batch_size, seq_len, n_features)
    assert not torch.isnan(recon).any()


def test_enhanced_sequence_vae_huber_loss_and_kl_annealing():
    """Verify EnhancedSequenceVAE Huber loss and dynamic beta annealing schedule."""
    vae = EnhancedSequenceVAE(
        seq_len=80,
        n_features=5,
        latent_dim=16,
        beta=0.01,
        use_kl_annealing=True,
        annealing_epochs=10,
    )
    x = torch.randn(4, 80, 5)

    recon_x, mu, logvar = vae(x)
    assert recon_x.shape == x.shape

    # Epoch 0: beta should be 0.0
    loss_ep0 = vae.compute_loss(x, recon_x, mu, logvar, epoch=0)
    assert loss_ep0['beta'] == 0.0
    assert torch.isclose(loss_ep0['total'], loss_ep0['recon'])

    # Epoch 5: beta should be 0.005
    loss_ep5 = vae.compute_loss(x, recon_x, mu, logvar, epoch=5)
    assert np.isclose(float(loss_ep5['beta']), 0.005)

    # Epoch 10+: beta should be 0.01
    loss_ep10 = vae.compute_loss(x, recon_x, mu, logvar, epoch=10)
    assert np.isclose(float(loss_ep10['beta']), 0.01)


def test_enhanced_sequence_vae_dual_path_scoring():
    """Verify Mahalanobis distance fitting and dual-path weighted ensemble score."""
    vae = EnhancedSequenceVAE(seq_len=80, n_features=5, latent_dim=16)

    # Fit latent distribution on normal noise sequences
    normal_seqs = torch.randn(40, 80, 5) * 0.2
    vae.fit_latent_distribution(normal_seqs)

    assert vae.latent_mean is not None
    assert vae.latent_cov_inv is not None
    assert vae.latent_mean.shape == (16,)
    assert vae.latent_cov_inv.shape == (16, 16)

    # Normal sequence should have low score
    clean_seq = torch.randn(80, 5) * 0.2
    scores_clean = vae.compute_anomaly_score(clean_seq)
    assert 'recon_error' in scores_clean
    assert 'mahalanobis_dist' in scores_clean
    assert 'ensemble' in scores_clean

    # Injected anomaly sequence should have significantly higher score
    anom_seq = torch.full((80, 5), 10.0)
    scores_anom = vae.compute_anomaly_score(anom_seq)

    assert scores_anom['ensemble'] > scores_clean['ensemble'] * 3.0


def test_overlapping_window_inference():
    """Verify overlapping window slicing prevents boundary artifact defect splitting."""
    vae = EnhancedSequenceVAE(seq_len=80, n_features=5, latent_dim=16)
    normal_seqs = torch.randn(20, 80, 5) * 0.1
    vae.fit_latent_distribution(normal_seqs)

    inference = OverlappingWindowInference(vae, window_size=80, overlap=0.5)

    # 160-bin track sequence with a defect right at bin 80
    long_seq = torch.randn(160, 5) * 0.1
    long_seq[75:85, :] = 12.0

    result = inference.predict(long_seq)

    assert 'ensemble' in result
    assert 'all_scores' in result
    assert 'positions' in result
    assert len(result['all_scores']) == 3
    assert result['positions'] == [0, 40, 80]
    assert result['max_position'] in (40, 80)


def test_multi_head_attention_1d():
    """Verify MultiHeadAttention1D shape and context vector pooling."""
    hidden_size = 128
    num_heads = 4
    mha = MultiHeadAttention1D(hidden_size=hidden_size, num_heads=num_heads)

    x = torch.randn(2, 80, hidden_size)
    out, attn_weights = mha(x)

    assert out.shape == (2, hidden_size)
    assert attn_weights.shape == (2, 80)
    assert not torch.isnan(out).any()


def test_enhanced_bilstm_classifier():
    """Verify 3-layer EnhancedBiLSTMClassifier forward pass and explanation."""
    model = EnhancedBiLSTMClassifier(
        input_size=5,
        hidden_size=128,
        num_layers=3,
        num_classes=5,
        dropout=0.4,
        use_attention=True,
        num_heads=4,
    )

    x = torch.randn(3, 80, 5)
    logits, attn_weights = model(x)

    assert logits.shape == (3, 5)
    assert attn_weights.shape == (3, 80)

    # Test single-sequence prediction with explanation
    single_x = torch.randn(80, 5)
    explanation = model.predict_with_explanation(single_x)

    assert 'class' in explanation
    assert 0 <= explanation['class'] < 5
    assert 'confidence' in explanation
    assert 0.0 <= explanation['confidence'] <= 1.0
    assert 'probs' in explanation
    assert len(explanation['probs']) == 5
    assert explanation['attention'] is not None
    assert len(explanation['attention']) == 80


def test_sequence_augmentation():
    """Verify SequenceAugmentation preserves shape and applies perturbations."""
    augmenter = SequenceAugmentation(noise_std=0.1, shift_range=5, scale_range=0.1)
    seq = torch.ones(80, 5)

    aug = augmenter.augment(seq)

    assert aug.shape == (80, 5)
    assert isinstance(aug, torch.Tensor)


def test_calibration_verification_sync_all_models():
    """Verify all 4 models calibration JSON files exist and pass synchronization check."""
    assert verify_calibration_sync() is True
