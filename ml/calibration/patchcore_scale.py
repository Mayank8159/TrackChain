# Sigmoid threshold calibration for PatchCore nearest-neighbor L2 distances (tc.v1 SOTA).

import json
import os
from pathlib import Path
from typing import List, Union, Dict, Any, Optional
import numpy as np


class SigmoidDistanceCalibrator:
    """
    Calibrates unbounded PatchCore L2 distance [0, inf) into a [0.0, 1.0] probability score.
    Uses Sigmoid Threshold Scaling based on the P99 threshold of normal validation images:
        Score = 1.0 / (1.0 + exp(-k * (d - T)))
    Where:
        d = raw L2 distance
        T = P99 threshold on normal validation data (1% FPR target)
        k = sigmoid steepness factor (default: 0.5)
    """

    def __init__(
        self,
        threshold: float = 10.0,
        steepness_k: float = 0.5,
        percentile: float = 99.0,
    ):
        self.threshold = float(threshold)
        self.steepness_k = float(steepness_k)
        self.percentile = float(percentile)
        self.is_fitted = False

    def fit(self, normal_distances: Union[List[float], np.ndarray], percentile: Optional[float] = None) -> float:
        """Fit baseline threshold T from normal validation distance distribution."""
        arr = np.asarray(normal_distances, dtype=np.float32)
        if len(arr) == 0:
            raise ValueError("Cannot fit calibrator on empty distance array.")

        target_p = percentile if percentile is not None else self.percentile
        self.percentile = target_p
        self.threshold = float(np.percentile(arr, target_p))
        self.is_fitted = True
        return self.threshold

    def scale(self, distance: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Convert raw L2 distance to [0.0, 1.0] calibrated anomaly score."""
        d = np.asarray(distance, dtype=np.float64)
        # Sigmoid: 1 / (1 + exp(-k * (d - T)))
        z = -self.steepness_k * (d - self.threshold)
        # Clip z to avoid numerical overflow in exp
        z_clipped = np.clip(z, -60.0, 60.0)
        score = 1.0 / (1.0 + np.exp(z_clipped))

        if np.ndim(distance) == 0:
            return float(score)
        return score

    def to_dict(self) -> Dict[str, Any]:
        """Serialize calibrator state."""
        return {
            "method": "sigmoid_threshold_scaling",
            "threshold_p99": self.threshold,
            "steepness_k": self.steepness_k,
            "percentile": self.percentile,
            "is_fitted": self.is_fitted,
        }

    def save(self, filepath: Union[str, Path]):
        """Save calibration parameters to JSON."""
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "SigmoidDistanceCalibrator":
        """Load calibration parameters from JSON."""
        p = Path(filepath)
        if not p.exists():
            return cls()
        with open(p, "r") as f:
            data = json.load(f)
        cal = cls(
            threshold=data.get("threshold_p99", 10.0),
            steepness_k=data.get("steepness_k", 0.5),
            percentile=data.get("percentile", 99.0),
        )
        cal.is_fitted = data.get("is_fitted", True)
        return cal
