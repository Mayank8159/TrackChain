# Sequence VAE trained on normal geometry to flag novel patterns.

from typing import Tuple
import torch
import torch.nn as nn
from ml.core.registry import register_model


@register_model("geometry_sequence_vae")
class SequenceVAE(nn.Module):
    """Variational Autoencoder trained exclusively on nominal track geometry to detect novel waveforms."""

    def __init__(
        self,
        input_dim: int = 6,
        hidden_dim: int = 32,
        latent_dim: int = 8,
    ):
        super().__init__()
        # Encoder
        self.encoder_rnn = nn.GRU(input_dim, hidden_dim, batch_first=True)
        self.fc_mu = nn.Linear(hidden_dim, latent_dim)
        self.fc_logvar = nn.Linear(hidden_dim, latent_dim)

        # Decoder
        self.decoder_fc = nn.Linear(latent_dim, hidden_dim)
        self.decoder_rnn = nn.GRU(hidden_dim, hidden_dim, batch_first=True)
        self.output_layer = nn.Linear(hidden_dim, input_dim)

    def encode(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        _, h_n = self.encoder_rnn(x)
        h = h_n[-1]
        return self.fc_mu(h), self.fc_logvar(h)

    def reparameterize(self, mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def decode(self, z: torch.Tensor, seq_len: int) -> torch.Tensor:
        h = self.decoder_fc(z).unsqueeze(1).repeat(1, seq_len, 1)
        out, _ = self.decoder_rnn(h)
        return self.output_layer(out)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        mu, logvar = self.encode(x)
        z = self.reparameterize(mu, logvar)
        recon_x = self.decode(z, x.size(1))
        return recon_x, mu, logvar

    def compute_anomaly_score(self, x: torch.Tensor) -> torch.Tensor:
        """Mean reconstruction error (MSE) across time and features."""
        with torch.no_grad():
            recon_x, _, _ = self.forward(x)
            mse = torch.mean((recon_x - x) ** 2, dim=(1, 2))
        return mse
