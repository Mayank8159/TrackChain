"""
ml/models/geometry/fault_classifier.py
Bi-LSTM with Temporal Attention for Geometry Fault Typing (tc.v1 SOTA).

Canonical single-source-of-truth module.  Contains BOTH architectures:
  • BiLSTMAttention            – lightweight single-LSTM-stack + linear attention
  • EnhancedBiLSTMClassifier   – deep 3-layer residual LSTM + multi-head attention

Plus training utilities (SequenceAugmentation).
Single Source of Truth: NUM_GEOMETRY_CLASSES = 6.
"""

import json
import os
from pathlib import Path
from typing import Dict, Tuple, Optional, Union, Any, List
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from ml.core.schema import CalibratedSignal, SignalType, DefectClass
from ml.core.registry import register_model

# Canonical single source of truth for geometry fault classification
NUM_GEOMETRY_CLASSES = 6


class BiLSTMAttention(nn.Module):
    """
    Bidirectional LSTM with Layer Normalization and Temporal Attention
    for geometry waveform sequence classification.
    """

    def __init__(
        self,
        input_size: int = 5,
        hidden_size: int = 128,
        num_layers: int = 3,
        num_classes: int = NUM_GEOMETRY_CLASSES,
        dropout: float = 0.3,
    ):
        super().__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.num_classes = num_classes

        self.norm = nn.LayerNorm(input_size)
        self.lstm = nn.LSTM(
            input_size,
            hidden_size,
            num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )

        # Attention mechanism
        self.attention = nn.Linear(hidden_size * 2, 1)

        # Classification head
        self.fc = nn.Linear(hidden_size * 2, num_classes)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        # x shape: (batch, seq_len, input_size)
        x = self.norm(x)
        lstm_out, _ = self.lstm(x)  # (batch, seq_len, hidden*2)

        # Calculate attention weights
        attn_scores = self.attention(lstm_out).squeeze(-1)  # (batch, seq_len)
        attn_weights = F.softmax(attn_scores, dim=1)        # (batch, seq_len)

        # Apply attention to get context vector
        context = torch.bmm(lstm_out.transpose(1, 2), attn_weights.unsqueeze(-1)).squeeze(-1)

        logits = self.fc(context)
        return logits, attn_weights


# Aliases for backwards compatibility
BiLSTMGeometryClassifier = BiLSTMAttention


@register_model("geometry_fault_classifier")
class GeometryFaultClassifier:
    """
    Inference & execution wrapper for the Bi-LSTM Geometry Fault Classifier.
    Emits strictly compliant tc.v1 CalibratedSignal items with explainable attention maps.
    """

    CLASS_MAP = {
        0: DefectClass.NORMAL,
        1: DefectClass.DIPPED_JOINT,
        2: DefectClass.CYCLIC_TOP,
        3: DefectClass.TWIST_FAULT,
        4: DefectClass.ALIGNMENT_KINK,
        5: DefectClass.BUCKLING_RISK,
    }

    def __init__(
        self,
        weights_path: Optional[Union[str, Path]] = "artifacts/checkpoints/geometry/bilstm_fault_typing_enhanced.pt",
        device: str = "cpu",
        num_classes: int = NUM_GEOMETRY_CLASSES,
        threshold: float = 0.60,
    ):
        self.device = torch.device(device if torch.cuda.is_available() or device == "cpu" else "cpu")
        self.threshold = threshold
        self.num_classes = num_classes

        self.model = BiLSTMAttention(num_classes=num_classes).to(self.device)

        # Resolve candidate weight paths in order of preference
        candidate_weights = [weights_path] if weights_path else []
        candidate_weights.extend([
            "artifacts/checkpoints/geometry/bilstm_fault_typing_enhanced.pt",
            "artifacts/checkpoints/geometry/bilstm_fault_typing.pt",
            "ml/models/geometry/weights/fault_classifier.pt",
            "ml/models/geometry/weights/bilstm_fault_typing_enhanced.pt",
        ])

        for wp in candidate_weights:
            if wp and os.path.exists(str(wp)):
                try:
                    ckpt = torch.load(wp, map_location=self.device)
                    state = ckpt["model_state_dict"] if isinstance(ckpt, dict) and "model_state_dict" in ckpt else ckpt
                    if isinstance(state, dict) and "lstm.weight_ih_l0" in state:
                        detected_hidden = state["lstm.weight_ih_l0"].shape[0] // 4
                        # Count layers
                        detected_layers = sum(1 for k in state.keys() if k.startswith("lstm.weight_ih_l") and not k.endswith("_reverse"))
                        if detected_hidden != self.model.hidden_size or detected_layers != self.model.num_layers:
                            self.model = BiLSTMAttention(hidden_size=detected_hidden, num_layers=max(1, detected_layers), num_classes=self.num_classes).to(self.device)
                    self.model.load_state_dict(state, strict=False)
                    if isinstance(ckpt, dict) and "temperature" in ckpt:
                        self.temperature = float(ckpt["temperature"])
                    break
                except Exception as e:
                    pass

        self.model.eval()
        self.temperature = 1.5
        self.vector_weights: Optional[np.ndarray] = None
        self.vector_biases: Optional[np.ndarray] = None

        # Check calibration files for calibrated vector scaling or temperature
        for cal_p in ["artifacts/calibration/bilstm_temp.json", "artifacts/calibration/params.json"]:
            if os.path.exists(cal_p):
                try:
                    import json
                    with open(cal_p, "r", encoding="utf-8") as f:
                        cal_data = json.load(f)
                    if "weights" in cal_data and "biases" in cal_data:
                        self.vector_weights = np.asarray(cal_data["weights"], dtype=np.float32)
                        self.vector_biases = np.asarray(cal_data["biases"], dtype=np.float32)
                    if "temperature" in cal_data:
                        self.temperature = float(cal_data["temperature"])
                        break
                    elif "bilstm_temperature" in cal_data:
                        self.temperature = float(cal_data["bilstm_temperature"])
                        break
                except Exception:
                    pass

        # Defensive guard: verify model output dimension matches calibration weights
        if self.vector_weights is not None:
            assert len(self.vector_weights) == self.num_classes, (
                f"Class-count mismatch: model={self.num_classes}, "
                f"calibration={len(self.vector_weights)}. Retrain or refit to align."
            )

    def _format_input(self, geometry_window: Union[np.ndarray, Dict[str, np.ndarray], torch.Tensor]) -> torch.Tensor:
        """Standardizes input geometry telemetry into shape [1, seq_len, 5]."""
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
                    cols.append(np.zeros(80))
            arr = np.column_stack(cols)
        elif isinstance(geometry_window, torch.Tensor):
            arr = geometry_window.cpu().numpy()
        else:
            arr = np.asarray(geometry_window)

        if arr.ndim == 2:
            arr = np.expand_dims(arr, axis=0)  # [1, seq_len, 5]

        # Resample or pad/slice to 80 bins
        b, t, c = arr.shape
        if t != 80:
            fixed = np.zeros((b, 80, c), dtype=np.float32)
            copy_len = min(t, 80)
            fixed[:, :copy_len, :] = arr[:, :copy_len, :]
            arr = fixed

        return torch.tensor(arr, dtype=torch.float32).to(self.device)

    def predict(self, geometry_window: Union[np.ndarray, Dict[str, np.ndarray], torch.Tensor]) -> CalibratedSignal:
        """
        geometry_window: shape (seq_len, 5) or (batch, seq_len, 5) or feature dict.
        Returns tc.v1 CalibratedSignal with attention explainability metadata.
        """
        with torch.no_grad():
            tensor_in = self._format_input(geometry_window)
            logits, attn_weights = self.model(tensor_in)
            logits_np = logits.cpu().numpy()[0]

            # Apply SOTA Vector Scaling (or fallback temperature scaling)
            if (
                self.vector_weights is not None
                and self.vector_biases is not None
                and len(self.vector_weights) == len(logits_np)
            ):
                scaled_logits_np = logits_np * self.vector_weights + self.vector_biases
                exp_logits = np.exp(scaled_logits_np - np.max(scaled_logits_np))
                probs = exp_logits / np.sum(exp_logits)
            else:
                scaled_logits = logits / max(1e-4, self.temperature)
                probs = F.softmax(scaled_logits, dim=1).cpu().numpy()[0]

            attn = attn_weights.cpu().numpy()[0]
            pred_idx = int(np.argmax(probs))
            confidence = float(probs[pred_idx])
            raw_confidence = float(F.softmax(logits, dim=1).cpu().numpy()[0, pred_idx])

            peak_bin = int(np.argmax(attn))
            label = self.CLASS_MAP.get(pred_idx, DefectClass.NORMAL)
            fired = bool((confidence >= self.threshold) and (pred_idx != 0))

            return CalibratedSignal(
                name="bilstm_geometry_typing",
                model_version="0.1.0",
                signal_type=SignalType.GEOMETRY_KNOWN_TYPE,
                value=confidence,
                raw_score=raw_confidence,
                threshold=self.threshold,
                fired=fired,
                label=label,
                bbox=None,
                explanation={
                    "attention_peak_bin": peak_bin,
                    "attention_peak_chainage_m": round(peak_bin * 0.25, 2),
                    "confidence": round(confidence, 4),
                },
                metadata={
                    "attention_peak_bin": peak_bin,
                    "attention_weights": [round(float(v), 4) for v in attn.tolist()],
                    "class_probabilities": {
                        self.CLASS_MAP.get(i, DefectClass.NORMAL).value: round(float(p), 4)
                        for i, p in enumerate(probs)
                    },
                },
            )


# Aliases for backwards compatibility
BiLSTMFaultClassifier = GeometryFaultClassifier
BiLSTMClassifier = GeometryFaultClassifier


# ---------------------------------------------------------------------------
# Architecture B: Enhanced Bi-LSTM (3-layer residual + multi-head attention)
# ---------------------------------------------------------------------------


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
        num_classes: int = NUM_GEOMETRY_CLASSES,
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


# ---------------------------------------------------------------------------
# Training Utilities
# ---------------------------------------------------------------------------


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
