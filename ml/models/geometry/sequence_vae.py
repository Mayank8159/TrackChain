"""
ml/models/geometry/sequence_vae.py
1D-CNN Variational Autoencoder (VAE) for Novel Geometry Anomaly Detection (tc.v1 SOTA).
Features:
  1. Dilated 1D-CNN Encoder (captures 1-3m, 3-10m, and 10-30m wavelengths)
  2. Dual-Path Anomaly Scoring (Reconstruction MSE + Latent Mahalanobis Distance)
  3. Sigmoid Distance Calibration for [0.0, 1.0] confidence mapping
"""

import os
from pathlib import Path
from typing import Dict, Tuple, Optional, Union, Any, List
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from ml.core.schema import CalibratedSignal, SignalType, DefectClass
from ml.core.registry import register_model
from ml.calibration.patchcore_scale import SigmoidDistanceCalibrator
from ml.models.geometry.sequence_vae_enhanced import EnhancedSequenceVAE


class DilatedEncoder(nn.Module):
    """
    Multi-Scale Dilated 1D-CNN Encoder capturing short (1-3m), medium (3-10m),
    and long (10-30m) spatial track wavelengths simultaneously.
    """

    def __init__(self, n_features: int = 5, seq_len: int = 80, latent_dim: int = 16):
        super().__init__()
        self.n_features = n_features
        self.seq_len = seq_len
        self.latent_dim = latent_dim

        # Parallel multi-scale dilated convolutions
        self.branch_short = nn.Conv1d(n_features, 32, kernel_size=3, dilation=1, padding=1)   # 1-3m wavelengths
        self.branch_medium = nn.Conv1d(n_features, 32, kernel_size=3, dilation=4, padding=4)  # 3-10m wavelengths
        self.branch_long = nn.Conv1d(n_features, 32, kernel_size=3, dilation=10, padding=10) # 10-30m wavelengths

        self.fusion = nn.Sequential(
            nn.Conv1d(96, 64, kernel_size=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool1d(20),  # Downsample sequence to 20 spatial bins
        )

        self.flat_size = 64 * 20  # 1280

        # Latent Space Projections
        self.fc_mu = nn.Linear(self.flat_size, latent_dim)
        self.fc_logvar = nn.Linear(self.flat_size, latent_dim)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        # x: [batch, n_features, seq_len]
        short = F.relu(self.branch_short(x))
        medium = F.relu(self.branch_medium(x))
        long = F.relu(self.branch_long(x))

        combined = torch.cat([short, medium, long], dim=1)  # [B, 96, seq_len]
        h = self.fusion(combined).flatten(1)               # [B, 1280]

        mu = self.fc_mu(h)
        logvar = self.fc_logvar(h)
        return mu, logvar


class SequenceVAE(nn.Module):
    """
    1D-CNN Variational Autoencoder with Dilated Multi-Scale Encoder
    and Transposed Conv1D Decoder for track geometry waveform reconstruction.
    """

    def __init__(
        self,
        seq_len: int = 80,
        n_features: int = 5,
        latent_dim: int = 16,
    ):
        super().__init__()
        self.seq_len = seq_len
        self.n_features = n_features
        self.latent_dim = latent_dim

        # Multi-scale dilated encoder
        self.encoder = DilatedEncoder(n_features=n_features, seq_len=seq_len, latent_dim=latent_dim)
        self.flat_size = self.encoder.flat_size

        # Decoder: Reconstructs 5-channel sequence back to 80 spatial bins
        self.decoder_input = nn.Linear(latent_dim, self.flat_size)
        self.decoder = nn.Sequential(
            nn.Unflatten(1, (64, 20)),
            nn.ConvTranspose1d(64, 32, kernel_size=3, stride=2, padding=1, output_padding=1),  # 20 -> 40
            nn.ReLU(),
            nn.ConvTranspose1d(32, n_features, kernel_size=3, stride=2, padding=1, output_padding=1),  # 40 -> 80
        )

    def reparameterize(self, mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        if x.dim() == 2:
            x = x.unsqueeze(0)

        # Transpose [batch, seq_len, features] -> [batch, features, seq_len] for Conv1d
        x_trans = x.transpose(1, 2)
        mu, logvar = self.encoder(x_trans)
        z = self.reparameterize(mu, logvar)

        h = F.relu(self.decoder_input(z))
        recon_trans = self.decoder(h)
        recon_x = recon_trans.transpose(1, 2)  # [batch, seq_len, features]

        return recon_x, mu, logvar

    def loss_function(
        self,
        recon_x: torch.Tensor,
        x: torch.Tensor,
        mu: torch.Tensor,
        logvar: torch.Tensor,
        beta: float = 0.01,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        if recon_x.shape != x.shape:
            min_len = min(recon_x.shape[1], x.shape[1])
            recon_x = recon_x[:, :min_len, :]
            x = x[:, :min_len, :]

        recon_loss = F.mse_loss(recon_x, x, reduction="mean")
        kld_loss = -0.5 * torch.mean(1 + logvar - mu.pow(2) - logvar.exp())
        total_loss = recon_loss + beta * kld_loss
        return total_loss, recon_loss, kld_loss

    def compute_reconstruction_error(self, x: torch.Tensor) -> torch.Tensor:
        self.eval()
        with torch.no_grad():
            recon_x, _, _ = self.forward(x)
            if recon_x.shape != x.shape:
                min_len = min(recon_x.shape[1], x.shape[1])
                recon_x = recon_x[:, :min_len, :]
                x = x[:, :min_len, :]
            error = torch.mean((recon_x - x) ** 2, dim=(1, 2))
        return error

    def compute_anomaly_score(self, x: torch.Tensor) -> torch.Tensor:
        """Alias for compute_reconstruction_error."""
        return self.compute_reconstruction_error(x)


@register_model("geometry_sequence_vae")
class SequenceVAEDetector:
    """
    Production detector wrapper for SequenceVAE featuring:
      - Enhanced multi-scale dilated convolutions matching trained SOTA checkpoint
      - Dual-Path Anomaly Scoring (Reconstruction MSE + Latent Mahalanobis Distance)
      - EVT & Sigmoid Calibration for calibrated [0.0, 1.0] novelty probabilities
    """

    def __init__(
        self,
        weights_path: Optional[Union[str, Path]] = "artifacts/checkpoints/geometry/sequence_vae_enhanced.pt",
        calibrator_path: Optional[Union[str, Path]] = "artifacts/calibration/vae_calibration.json",
        device: str = "cpu",
        seq_len: int = 80,
        n_features: int = 5,
        latent_dim: int = 16,
        alpha: float = 0.7,
        threshold: float = 0.50,
    ):
        self.device = torch.device(device if torch.cuda.is_available() or device == "cpu" else "cpu")
        self.seq_len = seq_len
        self.n_features = n_features
        self.latent_dim = latent_dim
        self.alpha = float(alpha)
        self.threshold = threshold

        # Default model is EnhancedSequenceVAE matching trained SOTA checkpoint ([128, 192, 1] fusion)
        self.model: Union[EnhancedSequenceVAE, SequenceVAE] = EnhancedSequenceVAE(
            seq_len=seq_len, n_features=n_features, latent_dim=latent_dim
        ).to(self.device)

        # Resolve candidate weight paths in order of preference
        candidate_weights = [weights_path] if weights_path else []
        candidate_weights.extend([
            "artifacts/checkpoints/geometry/sequence_vae_enhanced.pt",
            "artifacts/checkpoints/geometry/sequence_vae.pt",
            "ml/models/geometry/weights/sequence_vae.pt",
            "ml/models/geometry/weights/sequence_vae_enhanced.pt",
        ])

        loaded_checkpoint = False
        for wp in candidate_weights:
            if wp and os.path.exists(str(wp)):
                try:
                    ckpt = torch.load(wp, map_location=self.device)
                    state = ckpt["model_state_dict"] if isinstance(ckpt, dict) and "model_state_dict" in ckpt else ckpt
                    # Auto-detect architecture from state dict
                    if isinstance(state, dict) and "encoder.fusion.0.weight" in state:
                        in_channels = state["encoder.fusion.0.weight"].shape[1]
                        if in_channels == 96:
                            self.model = SequenceVAE(seq_len=seq_len, n_features=n_features, latent_dim=latent_dim).to(self.device)
                        else:
                            self.model = EnhancedSequenceVAE(seq_len=seq_len, n_features=n_features, latent_dim=latent_dim).to(self.device)
                    self.model.load_state_dict(state, strict=True)
                    loaded_checkpoint = True
                    break
                except Exception as e:
                    if weights_path is not None and str(wp) == str(weights_path):
                        raise RuntimeError(
                            f"VAE weight load FAILED for {weights_path} — architecture mismatch. "
                            f"Do NOT fall back to a random model. Error: {e}"
                        )

        self.model.eval()

        # Latent distribution baseline for Mahalanobis distance
        self.normal_latent_mean: Optional[np.ndarray] = None
        self.normal_latent_cov_inv: Optional[np.ndarray] = None

        # Sigmoid / EVT threshold calibrator
        self.calibrator = SigmoidDistanceCalibrator(threshold=1.65, steepness_k=2.0)
        candidate_calibs = [calibrator_path] if calibrator_path else []
        candidate_calibs.extend([
            "artifacts/calibration/vae_calibration.json",
            "artifacts/calibration/sequence_vae_calibration.json",
        ])
        loaded_calib = False
        for cp in candidate_calibs:
            if cp and os.path.exists(str(cp)):
                try:
                    with open(cp, "r", encoding="utf-8") as f:
                        cdata = json.load(f)
                    thresh = float(cdata.get("threshold_evt", cdata.get("threshold_p99", 1.65)))
                    k_val = float(cdata.get("steepness_k", cdata.get("steepness", 2.0)))
                    self.calibrator = SigmoidDistanceCalibrator(threshold=thresh, steepness_k=k_val)
                    if isinstance(self.model, EnhancedSequenceVAE):
                        self.model.threshold_evt = thresh
                        self.model.steepness_k = k_val
                    loaded_calib = True
                    break
                except Exception:
                    pass

        if not loaded_calib:
            # Auto-initialize baseline distribution on nominal noise
            synth_baseline = np.random.normal(0.0, 0.1, (30, self.seq_len, self.n_features)).astype(np.float32)
            self.fit_latent_distribution(synth_baseline)
            synth_scores = [self.compute_anomaly_score(s) for s in synth_baseline]
            self.calibrator.fit(synth_scores, percentile=99.0)
            self.calibrator.threshold = max(self.calibrator.threshold, 0.5)

    def _format_input(self, geometry_window: Union[np.ndarray, Dict[str, np.ndarray], torch.Tensor]) -> torch.Tensor:
        if isinstance(geometry_window, dict):
            keys = [
                ("twist_3m", "twist_3m_mm"),
                ("versine_10m", "versine_10m_mm"),
                ("versine_20m", "versine_20m_mm"),
                ("unevenness_10m", "unevenness_10m_mm"),
                ("cant", "cant_mm"),
            ]
            cols = []
            for k1, k2 in keys:
                if k1 in geometry_window:
                    cols.append(np.asarray(geometry_window[k1]))
                elif k2 in geometry_window:
                    cols.append(np.asarray(geometry_window[k2]))
                else:
                    cols.append(np.zeros(self.seq_len))
            arr = np.column_stack(cols)
        elif isinstance(geometry_window, torch.Tensor):
            arr = geometry_window.cpu().numpy()
        else:
            arr = np.asarray(geometry_window)

        if arr.ndim == 2:
            arr = np.expand_dims(arr, axis=0)  # [1, seq_len, 5]

        b, t, c = arr.shape
        if t != self.seq_len:
            fixed = np.zeros((b, self.seq_len, c), dtype=np.float32)
            copy_len = min(t, self.seq_len)
            fixed[:, :copy_len, :] = arr[:, :copy_len, :]
            arr = fixed

        return torch.tensor(arr, dtype=torch.float32).to(self.device)

    def fit_latent_distribution(self, normal_sequences: Union[np.ndarray, torch.Tensor, List[np.ndarray]]):
        """Fits baseline latent Gaussian distribution (mean and regularized inverse covariance)."""
        if isinstance(self.model, EnhancedSequenceVAE):
            if isinstance(normal_sequences, list):
                normal_tensor = torch.stack([torch.tensor(s, dtype=torch.float32) for s in normal_sequences])
            elif isinstance(normal_sequences, np.ndarray):
                normal_tensor = torch.tensor(normal_sequences, dtype=torch.float32)
            else:
                normal_tensor = normal_sequences
            self.model.fit_latent_distribution(normal_tensor)
            self.normal_latent_mean = self.model.latent_mean
            self.normal_latent_cov_inv = self.model.latent_cov_inv
            return

        self.model.eval()
        latents = []

        if isinstance(normal_sequences, list):
            normal_tensor = torch.stack([torch.tensor(s, dtype=torch.float32) for s in normal_sequences])
        elif isinstance(normal_sequences, np.ndarray):
            normal_tensor = torch.tensor(normal_sequences, dtype=torch.float32)
        else:
            normal_tensor = normal_sequences

        if normal_tensor.ndim == 2:
            normal_tensor = normal_tensor.unsqueeze(0)

        with torch.no_grad():
            normal_tensor = normal_tensor.to(self.device)
            _, mu, _ = self.model(normal_tensor)
            latents = mu.cpu().numpy()

        self.normal_latent_mean = np.mean(latents, axis=0)
        cov = np.cov(latents.T)
        if cov.ndim == 0:
            cov = np.array([[cov]])
        cov_reg = cov + np.eye(cov.shape[0]) * 1e-6
        self.normal_latent_cov_inv = np.linalg.inv(cov_reg)

    def compute_anomaly_score(self, sequence: Union[np.ndarray, Dict[str, np.ndarray], torch.Tensor]) -> float:
        """
        Computes Dual-Path Anomaly Score:
            Score = alpha * MSE_recon + (1 - alpha) * D_mahalanobis
        """
        if isinstance(self.model, EnhancedSequenceVAE):
            if isinstance(sequence, dict):
                tensor_in = self._format_input(sequence)
                res = self.model.compute_anomaly_score(tensor_in)
            else:
                res = self.model.compute_anomaly_score(sequence)
            return float(res.get("combined_score", res.get("recon_error", 0.0)))

        self.model.eval()
        tensor_in = self._format_input(sequence)

        with torch.no_grad():
            recon_x, mu, _ = self.model(tensor_in)
            mse = float(F.mse_loss(recon_x, tensor_in).item())

            # Path 2: Latent Mahalanobis Distance
            if self.normal_latent_mean is not None and self.normal_latent_cov_inv is not None:
                mu_np = mu.cpu().numpy()[0]
                diff = mu_np - self.normal_latent_mean
                mahal_dist = float(np.sqrt(np.clip(diff @ self.normal_latent_cov_inv @ diff.T, 0.0, None)))
            else:
                mahal_dist = float(torch.norm(mu).item())

        combined_score = float((self.alpha * mse) + ((1.0 - self.alpha) * mahal_dist))
        return combined_score

    def fit_calibration(self, normal_windows: Union[np.ndarray, torch.Tensor], percentile: float = 99.0):
        """Fits latent distribution and Sigmoid distance calibrator on nominal track validation sequences."""
        self.fit_latent_distribution(normal_windows)

        scores = []
        if isinstance(normal_windows, torch.Tensor):
            arr = normal_windows.cpu().numpy()
        else:
            arr = np.asarray(normal_windows)

        for seq in arr:
            scores.append(self.compute_anomaly_score(seq))

        self.calibrator.fit(scores, percentile=percentile)
        return self.calibrator.threshold

    def predict(self, geometry_window: Union[np.ndarray, Dict[str, np.ndarray], torch.Tensor]) -> CalibratedSignal:
        """
        Runs the 1D-CNN Dual-Path VAE on the 20m geometry window.
        Returns a calibrated CalibratedSignal indicating structural novelty.
        """
        if isinstance(self.model, EnhancedSequenceVAE):
            if isinstance(geometry_window, dict):
                tensor_in = self._format_input(geometry_window)
                pred = self.model.predict(tensor_in)
            else:
                pred = self.model.predict(geometry_window)
            raw_score = float(pred["raw_score"])
            calibrated_prob = float(pred["calibrated_prob"])
            is_anomaly = bool(pred["is_anomaly"])
            thresh = float(pred.get("threshold", self.threshold))
        else:
            raw_score = self.compute_anomaly_score(geometry_window)
            calibrated_prob = float(self.calibrator.scale(raw_score))
            is_anomaly = bool(calibrated_prob >= self.threshold)
            thresh = self.threshold

        explanation = {
            "combined_anomaly_score": round(raw_score, 4),
            "reconstruction_error": round(raw_score, 4),
            "calibrated_prob": round(calibrated_prob, 4),
            "p99_threshold": round(self.calibrator.threshold, 4),
            "anomaly_detected": is_anomaly,
        }

        return CalibratedSignal(
            name="sequence_vae_anomaly",
            stream_name="geometry_vae",
            model_version="0.1.0",
            signal_type=SignalType.GEOMETRY_NOVEL,
            value=calibrated_prob,
            raw_score=raw_score,
            calibrated_prob=calibrated_prob,
            threshold=thresh,
            fired=is_anomaly,
            is_anomaly=is_anomaly,
            predicted_class=DefectClass.GEOMETRY_ANOMALY if is_anomaly else DefectClass.NORMAL,
            bbox=None,
            explanation=explanation,
            metadata={
                "model_name": "sequence_vae_dual_path",
                "latent_dim": self.model.latent_dim,
                "combined_score": raw_score,
                "calibrator_threshold": self.calibrator.threshold,
            },
        )
