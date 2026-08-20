# Deterministic EN 13848 physics features: twist, cross-level, versine, unevenness.

from typing import Dict
import numpy as np


class EN13848PhysicsCalculator:
    """Computes deterministic track geometry quality metrics according to European Standard EN 13848-1/5."""

    def __init__(
        self,
        nominal_gauge_mm: float = 1435.0,
        twist_base_length_m: float = 3.0,
        chord_length_m: float = 10.0,
    ):
        self.nominal_gauge = nominal_gauge_mm
        self.twist_base_length_m = twist_base_length_m
        self.chord_length_m = chord_length_m

    def compute_gauge_deviation(self, raw_gauge_mm: np.ndarray) -> np.ndarray:
        """Track Gauge Deviation = Measured Gauge - Nominal Gauge (1435 mm)."""
        return raw_gauge_mm - self.nominal_gauge

    def compute_twist(
        self,
        cant_mm: np.ndarray,
        step_m: float = 0.25,
    ) -> np.ndarray:
        """Compute track twist in mm/m over the specified base length (typically 3m)."""
        base_samples = max(1, int(self.twist_base_length_m / step_m))
        twist = np.zeros_like(cant_mm)
        for i in range(base_samples, len(cant_mm)):
            twist[i] = (cant_mm[i] - cant_mm[i - base_samples]) / self.twist_base_length_m
        return twist

    def compute_chord_versine(
        self,
        alignment_mm: np.ndarray,
        step_m: float = 0.25,
    ) -> np.ndarray:
        """Compute 3-point chord offset (versine) representing alignment irregularity."""
        half_chord = max(1, int((self.chord_length_m / 2.0) / step_m))
        versine = np.zeros_like(alignment_mm)
        for i in range(half_chord, len(alignment_mm) - half_chord):
            midpoint_approx = (alignment_mm[i - half_chord] + alignment_mm[i + half_chord]) / 2.0
            versine[i] = alignment_mm[i] - midpoint_approx
        return versine

    def compute_track_quality_index(
        self,
        gauge_dev: np.ndarray,
        cant: np.ndarray,
        twist: np.ndarray,
        unevenness: np.ndarray,
    ) -> float:
        """Compute standard synthetic Track Quality Index (TQI) scaled 0-100."""
        std_g = np.std(gauge_dev)
        std_c = np.std(cant)
        std_t = np.std(twist)
        std_u = np.std(unevenness)
        # Lower standard deviations yield higher TQI score
        composite_error = (std_g * 1.2) + (std_c * 0.8) + (std_t * 2.0) + (std_u * 1.5)
        return float(np.clip(100.0 - composite_error * 4.0, 0.0, 100.0))
