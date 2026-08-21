"""
Enhanced Bi-LSTM Geometry Fault Classifier with:
- Deeper architecture (3 layers)
- Multi-head attention
- Label smoothing
- Residual connections
- Better initialization
- Gradient clipping
"""
import json
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


class MultiHeadAttention1D(nn.Module):
    """Multi-head attention for sequence classification."""

    def __init__(self, hidden_size: int, num_heads: int = 4):
        super().__init__()
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads

        self.qkv = nn.Linear(hidden_size, 3 * hidden_size)
        self.proj = nn.Linear(hidden_size, hidden_size)

        self.scale = self.head_dim ** -0.5

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            x: (batch, seq_len, hidden_size)
        Returns:
            output: (batch, hidden_size)
            attn_weights: (batch, seq_len)
        """
        B, T, C = x.shape

        # Compute Q, K, V
        qkv = self.qkv(x).reshape(B, T, 3, self.num_heads, self.head_dim)
        q, k, v = qkv.permute(2, 0, 3, 1, 4).unbind(0)

        # Attention
        attn = (q @ k.transpose(-2, -1)) * self.scale
        attn = attn.softmax(dim=-1)

        # Weighted sum
        out = (attn @ v).transpose(1, 2).reshape(B, T, C)
        out = self.proj(out)

        # Global pooling with attention weights
        attn_weights = attn.mean(dim=1).mean(dim=1)  # (batch, seq_len)
        # Global context vector via attention-weighted sum
        pooled = (out * attn_weights.unsqueeze(-1)).sum(dim=1)

        return pooled, attn_weights


class EnhancedBiLSTMClassifier(nn.Module):
    """
    Enhanced Bi-LSTM with:
    - 3 layers with residual connections
    - Multi-head attention
    - Layer normalization
    - Dropout
    """

    def __init__(
        self,
        input_size: int = 5,
        hidden_size: int = 128,
        num_layers: int = 3,
        num_classes: int = 5,
        dropout: float = 0.4,
        use_attention: bool = True,
        num_heads: int = 4,
    ):
        super().__init__()

        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.num_classes = num_classes
        self.use_attention = use_attention

        # Input projection
        self.input_proj = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.LayerNorm(hidden_size),
            nn.ReLU(),
        )

        # Bi-LSTM layers with residual connections
        self.lstm_layers = nn.ModuleList()
        self.layer_norms = nn.ModuleList()

        for i in range(num_layers):
            in_dim = hidden_size if i == 0 else hidden_size * 2
            self.lstm_layers.append(
                nn.LSTM(
                    input_size=in_dim,
                    hidden_size=hidden_size,
                    num_layers=1,
                    batch_first=True,
                    bidirectional=True,
                )
            )
            self.layer_norms.append(nn.LayerNorm(hidden_size * 2))

        # Attention
        if use_attention:
            self.attention = MultiHeadAttention1D(hidden_size * 2, num_heads)

        # Classification head
        self.classifier = nn.Sequential(
            nn.Linear(hidden_size * 2, hidden_size),
            nn.LayerNorm(hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(dropout / 2),
            nn.Linear(hidden_size // 2, num_classes),
        )

        # Initialize weights
        self._init_weights()

    def _init_weights(self):
        """Better weight initialization."""
        for name, param in self.named_parameters():
            if 'weight_ih' in name:
                nn.init.xavier_uniform_(param.data)
            elif 'weight_hh' in name:
                nn.init.orthogonal_(param.data)
            elif 'bias' in name:
                param.data.fill_(0)
                # Set forget gate bias to 1 for better gradient flow
                n = param.size(0)
                param.data[n // 4:n // 2].fill_(1)
            elif isinstance(param, nn.Linear):
                nn.init.xavier_uniform_(param.weight)
                if param.bias is not None:
                    nn.init.zeros_(param.bias)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        """
        Args:
            x: (batch, seq_len, input_size)
        Returns:
            logits: (batch, num_classes)
            attn_weights: (batch, seq_len) or None
        """
        # Input projection
        x = self.input_proj(x)

        # Bi-LSTM layers with residual connections
        for i, (lstm, norm) in enumerate(zip(self.lstm_layers, self.layer_norms)):
            residual = x
            x, _ = lstm(x)
            x = norm(x)

            # Residual connection (only if dimensions match)
            if i > 0 and residual.shape == x.shape:
                x = x + residual

        # Attention or global average pooling
        attn_weights = None
        if self.use_attention:
            x_pool, attn_weights = self.attention(x)
        else:
            x_pool = x.mean(dim=1)

        # Classification
        logits = self.classifier(x_pool)

        return logits, attn_weights

    def predict_with_explanation(self, x: torch.Tensor) -> Dict[str, Union[int, float, np.ndarray, None]]:
        """Predict with attention explanation."""
        self.eval()

        if x.dim() == 2:
            x = x.unsqueeze(0)

        with torch.no_grad():
            logits, attn_weights = self.forward(x)
            probs = F.softmax(logits, dim=1)
            pred_class = torch.argmax(probs, dim=1).item()
            confidence = probs[0, pred_class].item()

        return {
            'class': pred_class,
            'confidence': confidence,
            'probs': probs.cpu().numpy()[0],
            'attention': attn_weights.cpu().numpy()[0] if attn_weights is not None else None,
        }


class SequenceAugmentation:
    """Data augmentation for geometry sequences."""

    def __init__(self, noise_std: float = 0.1, shift_range: int = 5, scale_range: float = 0.1):
        self.noise_std = noise_std
        self.shift_range = shift_range
        self.scale_range = scale_range

    def augment(self, sequence: torch.Tensor) -> torch.Tensor:
        """Apply random augmentation to sequence."""
        aug = sequence.clone()

        # Random noise
        if np.random.random() < 0.5:
            noise = torch.randn_like(aug) * self.noise_std
            aug = aug + noise

        # Random shift
        if np.random.random() < 0.3:
            shift = np.random.randint(-self.shift_range, self.shift_range + 1)
            aug = torch.roll(aug, shift, dims=0)

        # Random scale
        if np.random.random() < 0.3:
            scale = 1.0 + np.random.uniform(-self.scale_range, self.scale_range)
            aug = aug * scale

        # Random channel dropout
        if np.random.random() < 0.2 and aug.shape[1] > 1:
            channel = np.random.randint(aug.shape[1])
            aug[:, channel] = 0

        return aug
