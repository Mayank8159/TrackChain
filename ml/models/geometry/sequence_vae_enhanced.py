"""
Enhanced Sequence VAE for Novel Geometry Anomaly Detection.

Upgrades from original:
- Dilated 1D CNN encoder for multi-scale wavelength capture
- KL annealing for stable training
- Dual-path scoring (reconstruction + Mahalanobis)
- Overlapping window inference
- Gradient clipping and learning rate scheduling
- Huber loss for robust reconstruction
"""
import json
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class DilatedEncoder1D(nn.Module):
    """
    Multi-scale 1D CNN encoder with dilated convolutions.
    Captures both short-wavelength (1-3m) and long-wavelength (10-30m) patterns.
    """

    def __init__(self, n_features: int = 5, seq_len: int = 80, latent_dim: int = 16):
        super().__init__()
        self.n_features = n_features
        self.seq_len = seq_len
        self.latent_dim = latent_dim

        # Multi-scale feature extraction with dilated convolutions
        # Branch 1: Short wavelengths (1-3m) - dilation=1
        self.branch_short = nn.Sequential(
            nn.Conv1d(n_features, 32, kernel_size=3, dilation=1, padding=1),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Conv1d(32, 64, kernel_size=3, dilation=1, padding=1),
            nn.BatchNorm1d(64),
            nn.ReLU(),
        )

        # Branch 2: Medium wavelengths (3-10m) - dilation=4
        self.branch_medium = nn.Sequential(
            nn.Conv1d(n_features, 32, kernel_size=3, dilation=4, padding=4),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Conv1d(32, 64, kernel_size=3, dilation=4, padding=4),
            nn.BatchNorm1d(64),
            nn.ReLU(),
        )

        # Branch 3: Long wavelengths (10-30m) - dilation=10
        self.branch_long = nn.Sequential(
            nn.Conv1d(n_features, 32, kernel_size=3, dilation=10, padding=10),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Conv1d(32, 64, kernel_size=3, dilation=10, padding=10),
            nn.BatchNorm1d(64),
            nn.ReLU(),
        )

        # Fuse multi-scale features
        self.fusion = nn.Sequential(
            nn.Conv1d(192, 128, kernel_size=1),  # 64*3 branches
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.AdaptiveAvgPool1d(8),  # Downsample to fixed length
        )

        # Latent space mapping
        self.flat_size = 128 * 8
        self.fc_mu = nn.Linear(self.flat_size, latent_dim)
        self.fc_logvar = nn.Linear(self.flat_size, latent_dim)

        # Initialize weights
        self._init_weights()

    def _init_weights(self):
        """Xavier initialization for better convergence."""
        for m in self.modules():
            if isinstance(m, nn.Conv1d):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            x: (batch, seq_len, n_features) or (batch, n_features, seq_len)
        Returns:
            mu, logvar: (batch, latent_dim)
        """
        if x.dim() == 2:
            x = x.unsqueeze(0)

        # Ensure (batch, channels, seq_len)
        if x.shape[1] == self.seq_len and x.shape[2] == self.n_features:
            x = x.transpose(1, 2)

        # Multi-scale feature extraction
        short = self.branch_short(x)
        medium = self.branch_medium(x)
        long = self.branch_long(x)

        # Concatenate along channel dimension
        combined = torch.cat([short, medium, long], dim=1)  # (batch, 192, seq_len)

        # Fuse and downsample
        h = self.fusion(combined)  # (batch, 128, 8)
        h = h.flatten(1)  # (batch, 1024)

        # Map to latent space
        mu = self.fc_mu(h)
        logvar = self.fc_logvar(h)

        return mu, logvar


class Decoder1D(nn.Module):
    """
    1D CNN decoder for sequence reconstruction.
    Uses transposed convolutions for upsampling.
    """

    def __init__(self, n_features: int = 5, seq_len: int = 80, latent_dim: int = 16):
        super().__init__()

        self.seq_len = seq_len
        self.n_features = n_features

        # Project from latent space
        self.decoder_input = nn.Sequential(
            nn.Linear(latent_dim, 128 * 8),
            nn.ReLU(),
        )

        # Upsample with transposed convolutions
        self.decoder = nn.Sequential(
            nn.Unflatten(1, (128, 8)),
            nn.ConvTranspose1d(128, 128, kernel_size=3, stride=2, padding=1, output_padding=1),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.ConvTranspose1d(128, 64, kernel_size=3, stride=2, padding=1, output_padding=1),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.ConvTranspose1d(64, 32, kernel_size=3, stride=2, padding=1, output_padding=1),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Conv1d(32, n_features, kernel_size=3, padding=1),
        )

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, (nn.Conv1d, nn.ConvTranspose1d)):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        """
        Args:
            z: (batch, latent_dim)
        Returns:
            recon_x: (batch, seq_len, n_features)
        """
        if z.dim() == 1:
            z = z.unsqueeze(0)

        h = self.decoder_input(z)  # (batch, 1024)
        recon = self.decoder(h)    # (batch, n_features, length)

        # Ensure correct sequence length
        if recon.shape[2] != self.seq_len:
            recon = F.interpolate(recon, size=self.seq_len, mode='linear', align_corners=False)

        return recon.transpose(1, 2)  # (batch, seq_len, n_features)


class EnhancedSequenceVAE(nn.Module):
    """
    Enhanced Sequence VAE with:
    - Multi-scale dilated encoder
    - KL annealing support
    - Huber loss for robust reconstruction
    - Dual-path anomaly scoring
    """

    def __init__(
        self,
        seq_len: int = 80,
        n_features: int = 5,
        latent_dim: int = 16,
        beta: float = 0.01,
        use_kl_annealing: bool = True,
        annealing_epochs: int = 10,
    ):
        super().__init__()

        self.seq_len = seq_len
        self.n_features = n_features
        self.latent_dim = latent_dim
        self.beta = beta
        self.use_kl_annealing = use_kl_annealing
        self.annealing_epochs = annealing_epochs

        # Encoder and Decoder
        self.encoder = DilatedEncoder1D(n_features, seq_len, latent_dim)
        self.decoder = Decoder1D(n_features, seq_len, latent_dim)

        # For dual-path scoring
        self.latent_mean: Optional[np.ndarray] = None
        self.latent_cov_inv: Optional[np.ndarray] = None

    def reparameterize(self, mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
        """Reparameterization trick."""
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Forward pass.

        Args:
            x: (batch, seq_len, n_features)
        Returns:
            recon_x, mu, logvar
        """
        if x.dim() == 2:
            x = x.unsqueeze(0)

        mu, logvar = self.encoder(x)
        z = self.reparameterize(mu, logvar)
        recon_x = self.decoder(z)

        return recon_x, mu, logvar

    def compute_loss(
        self,
        x: torch.Tensor,
        recon_x: torch.Tensor,
        mu: torch.Tensor,
        logvar: torch.Tensor,
        epoch: int = 0,
    ) -> Dict[str, torch.Tensor]:
        """
        Compute VAE loss with KL annealing.

        Args:
            x: Input sequence
            recon_x: Reconstructed sequence
            mu: Latent mean
            logvar: Latent log variance
            epoch: Current epoch (for KL annealing)

        Returns:
            Dictionary with total loss and components
        """
        if x.dim() == 2:
            x = x.unsqueeze(0)
        if recon_x.dim() == 2:
            recon_x = recon_x.unsqueeze(0)

        # Reconstruction loss (Huber for robustness to outliers)
        recon_loss = F.smooth_l1_loss(recon_x, x, reduction='sum') / x.size(0)

        # KL divergence
        kl_loss = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp()) / x.size(0)

        # KL annealing: gradually increase beta
        if self.use_kl_annealing and epoch < self.annealing_epochs:
            current_beta = self.beta * (epoch / self.annealing_epochs)
        else:
            current_beta = self.beta

        # Total loss
        total_loss = recon_loss + current_beta * kl_loss

        return {
            'total': total_loss,
            'recon': recon_loss,
            'kl': kl_loss,
            'beta': current_beta,
        }

    def fit_latent_distribution(self, normal_sequences: Union[torch.Tensor, np.ndarray]):
        """
        Fit the latent distribution from normal sequences.
        Used for Mahalanobis distance scoring.
        Device-agnostic execution with numerical epsilon covariance stabilization.
        """
        self.eval()
        if isinstance(normal_sequences, np.ndarray):
            normal_sequences = torch.tensor(normal_sequences, dtype=torch.float32)
        if normal_sequences.dim() == 2:
            normal_sequences = normal_sequences.unsqueeze(0)

        # Dynamically detect model device
        device = next(self.parameters()).device
        latents = []

        with torch.no_grad():
            for i in range(0, len(normal_sequences), 64):
                batch = normal_sequences[i:i + 64].to(device)
                mu, _ = self.encoder(batch)
                latents.append(mu.cpu())

        latents_arr = torch.cat(latents, dim=0).numpy()

        # Compute mean and inverse covariance with epsilon stabilization
        self.latent_mean = np.mean(latents_arr, axis=0)
        cov = np.cov(latents_arr.T)
        if cov.ndim == 0:
            cov = np.array([[cov]])
        cov_reg = cov + np.eye(latents_arr.shape[1]) * 1e-5
        self.latent_cov_inv = np.linalg.inv(cov_reg)

    def compute_anomaly_score(self, sequence: Union[torch.Tensor, np.ndarray]) -> Dict[str, float]:
        """
        Compute dual-path anomaly score (reconstruction + Mahalanobis).
        Device-agnostic execution.

        Args:
            sequence: (seq_len, n_features) or (batch, seq_len, n_features)

        Returns:
            Dictionary with scores
        """
        self.eval()
        if isinstance(sequence, np.ndarray):
            sequence = torch.tensor(sequence, dtype=torch.float32)
        if sequence.dim() == 2:
            sequence = sequence.unsqueeze(0)

        device = next(self.parameters()).device
        sequence = sequence.to(device)

        with torch.no_grad():
            recon_x, mu, logvar = self.forward(sequence)

            # Path 1: Reconstruction error (Huber loss)
            recon_error = F.smooth_l1_loss(recon_x, sequence, reduction='mean').item()

            # Path 2: Mahalanobis distance in latent space
            mu_np = mu.cpu().numpy()[0]

            if self.latent_mean is not None and self.latent_cov_inv is not None:
                diff = mu_np - self.latent_mean
                mahalanobis_dist = float(np.sqrt(np.clip(diff @ self.latent_cov_inv @ diff.T, 0.0, None)))
            else:
                mahalanobis_dist = recon_error  # Fallback

            return {
                'recon_error': recon_error,
                'mahalanobis_dist': mahalanobis_dist,
                'combined_score': 0.7 * recon_error + 0.3 * mahalanobis_dist,
            }

    @staticmethod
    def fit_evt_threshold(normal_errors: Union[List[float], np.ndarray], target_fpr: float = 0.01) -> Dict[str, float]:
        """
        Fit Extreme Value Theory (EVT) Peaks-Over-Threshold (POT) using Generalized Pareto Distribution (GPD).
        Mathematically models the tail of normal geometry error distribution.
        """
        from scipy.stats import genpareto
        errors_arr = np.asarray(normal_errors, dtype=np.float64)
        n_total = len(errors_arr)
        if n_total < 20:
            p99 = float(np.percentile(errors_arr, 99)) if n_total > 0 else 1.0
            return {"threshold": p99, "shape": 0.0, "scale": 1.0, "init_threshold": p99}

        # 1. Take top 10% (P90) as extreme tail
        threshold_init = float(np.percentile(errors_arr, 90.0))
        tail_excess = errors_arr[errors_arr > threshold_init] - threshold_init

        if len(tail_excess) < 5 or np.all(tail_excess == 0):
            p99 = float(np.percentile(errors_arr, 99.0))
            return {"threshold": p99, "shape": 0.0, "scale": 1.0, "init_threshold": threshold_init}

        # 2. Fit Generalized Pareto Distribution (GPD) to the tail
        try:
            shape, loc, scale = genpareto.fit(tail_excess, floc=0)
            n_tail = len(tail_excess)
            prob_excess = n_tail / n_total

            # 3. Calculate exact EVT quantile for target_fpr
            if abs(shape) < 1e-4:  # Exponential limit
                evt_threshold = threshold_init - scale * np.log(target_fpr / prob_excess)
            else:
                term = (target_fpr / prob_excess) ** (-shape) - 1.0
                evt_threshold = threshold_init + (scale / shape) * term

            evt_threshold = float(np.clip(evt_threshold, threshold_init, None))
        except Exception:
            evt_threshold = float(np.percentile(errors_arr, 99.0))
            shape, scale = 0.0, 1.0

        return {
            "threshold": evt_threshold,
            "shape": float(shape),
            "scale": float(scale),
            "init_threshold": float(threshold_init),
        }


class OverlappingWindowInference:
    """
    Inference with overlapping windows to prevent boundary-splitting.
    """

    def __init__(self, model: EnhancedSequenceVAE, window_size: int = 80, overlap: float = 0.5):
        self.model = model
        self.window_size = window_size
        self.stride = int(window_size * (1 - overlap))

    def predict(self, sequence: torch.Tensor) -> Dict[str, Union[float, list, int]]:
        """
        Predict with overlapping windows.

        Args:
            sequence: (total_len, n_features)

        Returns:
            Maximum anomaly score across all windows
        """
        seq_len = len(sequence)

        if seq_len < self.window_size:
            # Pad if too short
            padding = torch.zeros(self.window_size - seq_len, sequence.shape[1], dtype=sequence.dtype, device=sequence.device)
            sequence = torch.cat([sequence, padding], dim=0)
            seq_len = len(sequence)

        # Extract overlapping windows
        windows = []
        positions = []

        for start in range(0, seq_len - self.window_size + 1, self.stride):
            window = sequence[start:start + self.window_size]
            windows.append(window)
            positions.append(start)

        if not windows:
            windows = [sequence[:self.window_size]]
            positions = [0]

        # Score each window
        scores = []
        for window in windows:
            score = self.model.compute_anomaly_score(window)
            scores.append(score['ensemble'])

        # Return maximum score (most anomalous window)
        max_score = max(scores)

        return {
            'ensemble': max_score,
            'all_scores': scores,
            'positions': positions,
            'max_position': positions[scores.index(max_score)],
        }
