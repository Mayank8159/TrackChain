"""
ml/models/geometry/fault_classifier.py
Bi-LSTM with Temporal Attention for Geometry Fault Typing (tc.v1 SOTA).
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


class BiLSTMAttention(nn.Module):
    """
    Bidirectional LSTM with Layer Normalization and Temporal Attention
    for geometry waveform sequence classification.
    """

    def __init__(
        self,
        input_size: int = 5,
        hidden_size: int = 64,
        num_layers: int = 2,
        num_classes: int = 5,
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


# Alias for backwards compatibility
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
        weights_path: Optional[Union[str, Path]] = "artifacts/checkpoints/geometry/bilstm_fault_typing.pt",
        device: str = "cpu",
        num_classes: int = 5,
        threshold: float = 0.60,
    ):
        self.device = torch.device(device if torch.cuda.is_available() or device == "cpu" else "cpu")
        self.threshold = threshold
        self.num_classes = num_classes

        self.model = BiLSTMAttention(num_classes=num_classes).to(self.device)

        # Resolve candidate weight paths
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
                    self.model.load_state_dict(state, strict=False)
                    if isinstance(ckpt, dict) and "temperature" in ckpt:
                        self.temperature = float(ckpt["temperature"])
                    break
                except Exception as e:
                    print(f"[Warn] Could not load weights from {wp}: {e}")

        self.model.eval()
        self.temperature = 1.5

        # Check calibration files for calibrated temperature
        for cal_p in ["artifacts/calibration/bilstm_temp.json", "artifacts/calibration/params.json"]:
            if os.path.exists(cal_p):
                try:
                    import json
                    with open(cal_p, "r", encoding="utf-8") as f:
                        cal_data = json.load(f)
                    if "temperature" in cal_data:
                        self.temperature = float(cal_data["temperature"])
                        break
                    elif "bilstm_temperature" in cal_data:
                        self.temperature = float(cal_data["bilstm_temperature"])
                        break
                except Exception:
                    pass

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

            # Apply temperature scaling for calibration
            scaled_logits = logits / self.temperature
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
                        self.CLASS_MAP.get(i, DefectClass.NORMAL).value: round(float(probs[i]), 4)
                        for i in range(len(probs))
                    },
                },
            )
