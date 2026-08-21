# Sigmoid and Weibull threshold calibration for PatchCore nearest-neighbor L2 distances (tc.v1 SOTA).
# SOTA: Implements Weibull Extreme Value Distribution CDF to model high-dimensional L2 distance tails.

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
        z = -self.steepness_k * (d - self.threshold)
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
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "SigmoidDistanceCalibrator":
        """Load calibration parameters from JSON."""
        p = Path(filepath)
        if not p.exists():
            return cls()
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        cal = cls(
            threshold=data.get("threshold_p99", 10.0),
            steepness_k=data.get("steepness_k", 0.5),
            percentile=data.get("percentile", 99.0),
        )
        cal.is_fitted = data.get("is_fitted", True)
        return cal


class WeibullDistanceCalibrator:
    """
    SOTA Weibull Extreme Value Distribution CDF Calibrator.
    Maps high-dimensional (1536-d) PatchCore L2 distances into [0.0, 1.0] probability space:
        Score = 1.0 - exp(-(d / lambda)^k)
    Where:
        d = raw L2 distance
        lambda = Weibull scale parameter
        k = Weibull shape parameter
    """

    def __init__(self, shape_k: float = 2.0, scale_lambda: float = 20.0, p99_threshold: float = 21.0):
        self.shape_k = float(shape_k)
        self.scale_lambda = float(scale_lambda)
        self.p99_threshold = float(p99_threshold)
        self.is_fitted = False

    def fit(self, normal_distances: Union[List[float], np.ndarray]) -> Dict[str, float]:
        from scipy.stats import weibull_min
        arr = np.asarray(normal_distances, dtype=np.float64)
        if len(arr) == 0:
            raise ValueError("Cannot fit calibrator on empty distance array.")

        try:
            shape, loc, scale = weibull_min.fit(arr, floc=0)
            self.shape_k = float(shape)
            self.scale_lambda = float(scale)
        except Exception:
            self.shape_k = 2.0
            self.scale_lambda = float(np.mean(arr))

        self.p99_threshold = float(np.percentile(arr, 99.0))
        self.is_fitted = True
        return {"shape_k": self.shape_k, "scale_lambda": self.scale_lambda, "p99_threshold": self.p99_threshold}

    def scale(self, distance: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        d = np.asarray(distance, dtype=np.float64)
        z = np.power(np.clip(d / (self.scale_lambda + 1e-8), 0.0, 100.0), self.shape_k)
        score = 1.0 - np.exp(-np.clip(z, 0.0, 60.0))
        if np.ndim(distance) == 0:
            return float(score)
        return score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": "weibull_cdf",
            "shape_k": self.shape_k,
            "scale_lambda": self.scale_lambda,
            "threshold_p99": self.p99_threshold,
            "is_fitted": self.is_fitted,
        }

    def save(self, filepath: Union[str, Path]):
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "WeibullDistanceCalibrator":
        p = Path(filepath)
        if not p.exists():
            return cls()
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        cal = cls(
            shape_k=data.get("shape_k", 2.0),
            scale_lambda=data.get("scale_lambda", 20.0),
            p99_threshold=data.get("threshold_p99", 21.0),
        )
        cal.is_fitted = data.get("is_fitted", True)
        return cal
