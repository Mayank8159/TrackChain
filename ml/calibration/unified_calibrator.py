"""
ml/calibration/unified_calibrator.py
Central Unified Calibration Manager for all TrackChain vision and geometry models (tc.v1 SOTA).
Synchronizes all 5 model outputs into the unified [0.0, 1.0] probability space.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import numpy as np

from ml.core.schema import CalibratedSignal, SignalType
from ml.calibration.temperature import TemperatureScaler, VectorScaler
from ml.calibration.patchcore_scale import SigmoidDistanceCalibrator, WeibullDistanceCalibrator
from ml.calibration.fpr_threshold import FPRThresholdCalibrator


class UnifiedCalibrator:
    """
    Coordinates and executes calibration transforms across all models:
      - YOLOv8 (Temperature Scaling)
      - PatchCore (Weibull CDF / Sigmoid Distance P99)
      - EN 13848 Physics (Deterministic Exceedance Ratio)
      - Bi-LSTM (Vector Scaling / Temperature Scaling)
      - Sequence VAE (Extreme Value Theory EVT / P99 Dual-Path)
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
            stream_key = getattr(sig, "stream_name", getattr(sig, "name", None))
            if stream_key and stream_key in self.calibrators:
                cal_prob = self.calibrate(stream_key, sig.raw_score if hasattr(sig, "raw_score") else sig.value)
                sig.value = cal_prob
                sig.fired = bool(cal_prob >= sig.threshold)
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
        with open(p, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "UnifiedCalibrator":
        """Loads unified calibrator from JSON."""
        uc = cls()
        p = Path(filepath)
        if not p.exists():
            return uc
        with open(p, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        for name, cfg in manifest.items():
            method = cfg.get("method")
            if method == "sigmoid_threshold_scaling":
                uc.register_model(name, SigmoidDistanceCalibrator(
                    threshold=cfg.get("threshold_p99", 2.0),
                    steepness_k=cfg.get("steepness_k", 2.0),
                ))
            elif method == "weibull_cdf":
                uc.register_model(name, WeibullDistanceCalibrator(
                    shape_k=cfg.get("shape_k", 2.0),
                    scale_lambda=cfg.get("scale_lambda", 20.0),
                    p99_threshold=cfg.get("threshold_p99", 21.0),
                ))
            elif method == "vector_scaling":
                uc.register_model(name, VectorScaler.from_dict(cfg))
            elif method == "temperature_scaling":
                uc.register_model(name, TemperatureScaler(temperature=cfg.get("T", 1.5)))
        return uc
