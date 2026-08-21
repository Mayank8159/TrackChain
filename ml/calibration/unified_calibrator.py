"""
ml/calibration/unified_calibrator.py
Central Unified Calibration Manager for all TrackChain vision and geometry models (tc.v1 SOTA).
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import numpy as np

from ml.core.schema import CalibratedSignal, SignalType
from ml.calibration.temperature import TemperatureScaler
from ml.calibration.patchcore_scale import SigmoidDistanceCalibrator
from ml.calibration.fpr_threshold import FPRThresholdCalibrator


class UnifiedCalibrator:
    """
    Coordinates and executes calibration transforms across all models:
      - YOLOv8 (Temperature Scaling)
      - PatchCore (Sigmoid Distance P99)
      - EN 13848 Physics (Deterministic Exceedance Ratio)
      - Bi-LSTM (Temperature Scaling)
      - Sequence VAE (Sigmoid Dual-Path Anomaly Distance)
    """

    def __init__(self):
        self.calibrators: Dict[str, Any] = {}

    def register_model(self, model_name: str, calibrator: Any):
        """Register a calibration object for a named model or stream."""
        self.calibrators[model_name] = calibrator

    def calibrate(self, model_name: str, raw_score: float) -> float:
        """Calibrate a single raw score from a registered model."""
        if model_name not in self.calibrators:
            return float(np.clip(raw_score, 0.0, 1.0))

        cal = self.calibrators[model_name]
        if hasattr(cal, "scale"):
            return float(cal.scale(raw_score))
        elif hasattr(cal, "calibrate_probs"):
            probs = cal.calibrate_probs(np.array([[raw_score, 0.0]]))
            return float(probs[0, 0])
        elif hasattr(cal, "temperature"):
            T = float(cal.temperature.item()) if hasattr(cal.temperature, "item") else float(cal.temperature)
            return float(1.0 / (1.0 + np.exp(-raw_score / max(T, 1e-4))))
        return float(np.clip(raw_score, 0.0, 1.0))

    def calibrate_all(self, signals: List[CalibratedSignal]) -> List[CalibratedSignal]:
        """Iterates over a list of signals and updates calibrated probabilities."""
        for sig in signals:
            if sig.stream_name in self.calibrators:
                sig.calibrated_prob = self.calibrate(sig.stream_name, sig.raw_score)
                sig.is_anomaly = bool(sig.calibrated_prob >= sig.threshold)
        return signals

    def save(self, filepath: Union[str, Path]):
        """Serializes calibration configuration to JSON."""
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        manifest = {}
        for name, cal in self.calibrators.items():
            if hasattr(cal, "to_dict"):
                manifest[name] = cal.to_dict()
            elif hasattr(cal, "temperature"):
                T = float(cal.temperature.item()) if hasattr(cal.temperature, "item") else float(cal.temperature)
                manifest[name] = {"method": "temperature_scaling", "T": T}
        with open(p, "w") as f:
            json.dump(manifest, f, indent=2)

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "UnifiedCalibrator":
        """Loads unified calibrator from JSON."""
        uc = cls()
        p = Path(filepath)
        if not p.exists():
            return uc
        with open(p, "r") as f:
            manifest = json.load(f)
        for name, cfg in manifest.items():
            method = cfg.get("method")
            if method == "sigmoid_threshold_scaling":
                uc.register_model(name, SigmoidDistanceCalibrator(
                    threshold=cfg.get("threshold_p99", 2.0),
                    steepness_k=cfg.get("steepness_k", 2.0),
                ))
        return uc
