# Train the sequence VAE on normal geometry windows.

import torch
import torch.optim as optim
import numpy as np
from ml.models.geometry.sequence_vae import SequenceVAE
from ml.data.synthetic import generate_synthetic_geometry
from ml.utils.logging import get_ml_logger

logger = get_ml_logger("train_sequence_vae")


def train_vae(epochs: int = 10):
    logger.info("Training Sequence VAE on normal-only geometry windows...")
    raw = generate_synthetic_geometry(length_m=4000.0, fault_probability=0.0)

    seq_len = 100
    n_windows = len(raw["chainage_m"]) // seq_len
    features = np.stack([
        raw["gauge_mm"],
        raw["cant_mm"],
        raw["twist_mm_per_m"],
        raw["vertical_unevenness_mm"],
        raw["alignment_mm"],
        raw["vibration_rms_g"],
    ], axis=1)

    X = torch.from_numpy(features[:n_windows * seq_len].reshape(n_windows, seq_len, 6)).float()
    vae = SequenceVAE(input_dim=6, hidden_dim=32, latent_dim=8)
    optimizer = optim.Adam(vae.parameters(), lr=1e-3)

    for epoch in range(epochs):
        optimizer.zero_grad()
        recon_x, mu, logvar = vae(X)
        recon_loss = torch.mean((recon_x - X) ** 2)
        kl_loss = -0.5 * torch.mean(1 + logvar - mu.pow(2) - logvar.exp())
        loss = recon_loss + 0.01 * kl_loss
        loss.backward()
        optimizer.step()
        logger.info(f"Epoch {epoch+1}/{epochs} | VAE Loss: {loss.item():.4f}")

    torch.save(vae.state_dict(), "artifacts/checkpoints/sequence_vae.pt")
    logger.info("Sequence VAE saved to artifacts/checkpoints/sequence_vae.pt")


if __name__ == "__main__":
    train_vae()
