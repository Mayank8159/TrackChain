# Bi-LSTM that types flagged geometry windows from physics features.

import torch
import torch.nn as nn
from ml.core.registry import register_model


@register_model("geometry_fault_classifier")
class BiLSTMGeometryClassifier(nn.Module):
    """Bidirectional LSTM sequence classifier for categorizing track geometry waveforms into defect classes."""

    def __init__(
        self,
        input_dim: int = 6,
        hidden_dim: int = 64,
        num_layers: int = 2,
        num_classes: int = 4,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim * 2, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: [batch_size, seq_len, input_dim]
        lstm_out, (hn, cn) = self.lstm(x)
        # Global temporal average pooling
        pooled = torch.mean(lstm_out, dim=1)
        logits = self.fc(pooled)
        return logits
