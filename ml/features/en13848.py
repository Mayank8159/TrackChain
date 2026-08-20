# Deterministic EN 13848 & RDSO track geometry physics calculator (tc.v1 SOTA).

from typing import Dict, Optional, Tuple, Union, Any
import numpy as np
from scipy.signal import butter, filtfilt
from scipy.ndimage import uniform_filter1d


class EN13848PhysicsCalculator:
    """
    Computes deterministic railway track geometry quality metrics according to
    European Standard EN 13848-1/5 and Indian Railways RDSO standards.
    Fully vectorized in NumPy for real-time edge processing.
    """

    def __init__(
        self,
        nominal_gauge_mm: float = 1676.0,  # Default Indian Broad Gauge (1676mm)
        twist_bases_m: Tuple[float, ...] = (3.0, 6.0),
        versine_chords_m: Tuple[float, ...] = (10.0, 20.0),
        unevenness_chords_m: Tuple[float, ...] = (10.0, 30.0),
        highpass_cutoff_m: float = 70.0,
    ):
        self.nominal_gauge = nominal_gauge_mm
        self.twist_bases = twist_bases_m
        self.versine_chords = versine_chords_m
        self.unevenness_chords = unevenness_chords_m
        self.highpass_cutoff_m = highpass_cutoff_m

    def compute_cross_level(self, roll_rad: np.ndarray) -> np.ndarray:
        """
        Compute cross-level (cant) in mm from IMU roll angle:
            Cant(x) = Nominal_Gauge * sin(Roll(x))
        """
        return self.nominal_gauge * np.sin(roll_rad)

    def compute_gauge_deviation(self, raw_gauge_mm: np.ndarray) -> np.ndarray:
        """
        Track Gauge Deviation = Measured Gauge - Nominal Gauge.
        Positive = Gauge Widening; Negative = Gauge Tightening.
        """
        return raw_gauge_mm - self.nominal_gauge

    def compute_twist(
        self,
        cant_mm: np.ndarray,
        base_length_m: float = 3.0,
        step_m: float = 0.25,
        as_rate: bool = False,
    ) -> np.ndarray:
        """
        Compute track twist over a base length b (e.g. 3m or 6m):
            Twist(x, b) = Cant(x) - Cant(x - b)  [in mm]
        If as_rate=True, returns mm/m: (Cant(x) - Cant(x - b)) / b.
        Vectorized via NumPy slicing and zero-padding for initial boundary.
        """
        base_samples = max(1, int(round(base_length_m / step_m)))
        twist = np.zeros_like(cant_mm)
        if len(cant_mm) > base_samples:
            diff = cant_mm[base_samples:] - cant_mm[:-base_samples]
            if as_rate:
                diff = diff / base_length_m
            twist[base_samples:] = diff
        return twist

    def filter_macro_curvature(
        self,
        signal_mm: np.ndarray,
        step_m: float = 0.25,
        cutoff_wavelength_m: Optional[float] = None,
    ) -> np.ndarray:
        """
        High-pass filter to remove intentional track design curves (>70m wavelength),
        isolating localized track irregularities and defect versines.
        """
        cutoff_m = cutoff_wavelength_m or self.highpass_cutoff_m
        fs = 1.0 / step_m  # Spatial sampling frequency (cycles/m)
        f_cutoff = 1.0 / cutoff_m  # Cutoff frequency (cycles/m)
        nyquist = 0.5 * fs

        if len(signal_mm) >= int(cutoff_m / step_m) and len(signal_mm) > 30:
            window_size = int(cutoff_m / step_m)
            design_curve = uniform_filter1d(signal_mm, size=window_size, mode="nearest")
            return signal_mm - design_curve

        if f_cutoff >= nyquist or len(signal_mm) < 15:
            # Short window fallback to linear detrending
            x = np.arange(len(signal_mm))
            if len(x) > 1:
                p = np.polyfit(x, signal_mm, 1)
                return signal_mm - (p[0] * x + p[1])
            return signal_mm - np.mean(signal_mm)

        norm_cutoff = min(0.99, f_cutoff / nyquist)
        b, a = butter(N=2, Wn=norm_cutoff, btype="highpass")
        padlen = min(len(signal_mm) - 1, 12)
        return filtfilt(b, a, signal_mm, padlen=padlen)

    def compute_chord_versine(
        self,
        lateral_pos_mm: np.ndarray,
        chord_length_m: float = 10.0,
        step_m: float = 0.25,
        filter_curvature: bool = True,
    ) -> np.ndarray:
        """
        Compute 3-point chord offset (Versine) representing alignment irregularity:
            V_lat(x, L) = y(x) - [y(x - L/2) + y(x + L/2)] / 2.0
        Vectorized using boundary-clamped shifts.
        """
        y = self.filter_macro_curvature(lateral_pos_mm, step_m) if filter_curvature else lateral_pos_mm
        half_chord_samples = max(1, int(round((chord_length_m / 2.0) / step_m)))

        versine = np.zeros_like(y)
        n = len(y)
        if n > 2 * half_chord_samples:
            left_shifted = y[:-2 * half_chord_samples]
            right_shifted = y[2 * half_chord_samples:]
            center = y[half_chord_samples:n - half_chord_samples]
            midpoint = (left_shifted + right_shifted) / 2.0
            versine[half_chord_samples:n - half_chord_samples] = center - midpoint

        return versine

    def compute_longitudinal_unevenness(
        self,
        vertical_pos_mm: np.ndarray,
        chord_length_m: float = 10.0,
        step_m: float = 0.25,
    ) -> np.ndarray:
        """
        Compute vertical unevenness (Longitudinal Level) over a 3-point chord:
            V_vert(x, L) = z(x) - [z(x - L/2) + z(x + L/2)] / 2.0
        """
        return self.compute_chord_versine(
            vertical_pos_mm,
            chord_length_m=chord_length_m,
            step_m=step_m,
            filter_curvature=False,
        )

    def compute_all_features(
        self,
        roll_rad: np.ndarray,
        lateral_pos_mm: np.ndarray,
        vertical_pos_mm: np.ndarray,
        gauge_mm: np.ndarray,
        step_m: float = 0.25,
    ) -> Dict[str, Union[np.ndarray, float]]:
        """
        Extract complete EN 13848 / RDSO geometry feature suite from resampled arrays.
        """
        cant = self.compute_cross_level(roll_rad)
        gauge_dev = self.compute_gauge_deviation(gauge_mm)

        features: Dict[str, Union[np.ndarray, float]] = {
            "cant_mm": cant,
            "gauge_dev_mm": gauge_dev,
            "twist_3m_mm": self.compute_twist(cant, base_length_m=3.0, step_m=step_m),
            "twist_6m_mm": self.compute_twist(cant, base_length_m=6.0, step_m=step_m),
            "versine_10m_mm": self.compute_chord_versine(lateral_pos_mm, chord_length_m=10.0, step_m=step_m),
            "versine_20m_mm": self.compute_chord_versine(lateral_pos_mm, chord_length_m=20.0, step_m=step_m),
            "unevenness_10m_mm": self.compute_longitudinal_unevenness(vertical_pos_mm, chord_length_m=10.0, step_m=step_m),
            "unevenness_30m_mm": self.compute_longitudinal_unevenness(vertical_pos_mm, chord_length_m=30.0, step_m=step_m),
        }

        # Track Quality Index (TQI)
        features["tqi"] = self.compute_track_quality_index(
            gauge_dev=gauge_dev,
            cant=cant,
            twist=features["twist_3m_mm"],
            unevenness=features["unevenness_10m_mm"],
            versine=features["versine_10m_mm"],
        )

        return features

    def compute(
        self,
        telemetry_dict: Dict[str, np.ndarray],
        step_m: float = 0.25,
    ) -> Dict[str, Union[np.ndarray, float]]:
        """
        Convenience method to compute all features directly from a telemetry dictionary.
        """
        n = len(next(iter(telemetry_dict.values()))) if telemetry_dict else 0
        roll = telemetry_dict.get("roll_rad", np.zeros(n))
        lat = telemetry_dict.get("lateral_pos_mm", telemetry_dict.get("lat_accel_g", np.zeros(n)))
        vert = telemetry_dict.get("vertical_pos_mm", telemetry_dict.get("vert_accel_g", np.zeros(n)))
        gauge = telemetry_dict.get("gauge_mm", np.full(n, self.nominal_gauge))

        if "distances" in telemetry_dict and len(telemetry_dict["distances"]) > 1:
            step_m = float(np.mean(np.diff(telemetry_dict["distances"])))

        return self.compute_all_features(
            roll_rad=roll,
            lateral_pos_mm=lat,
            vertical_pos_mm=vert,
            gauge_mm=gauge,
            step_m=step_m,
        )

    def compute_track_quality_index(
        self,
        gauge_dev: np.ndarray,
        cant: np.ndarray,
        twist: np.ndarray,
        unevenness: np.ndarray,
        versine: Optional[np.ndarray] = None,
    ) -> float:
        """
        Compute standard synthetic Track Quality Index (TQI) scaled 0-100 (100 = perfect track).
        """
        std_g = float(np.std(gauge_dev)) if len(gauge_dev) > 0 else 0.0
        std_c = float(np.std(cant)) if len(cant) > 0 else 0.0
        std_t = float(np.std(twist)) if len(twist) > 0 else 0.0
        std_u = float(np.std(unevenness)) if len(unevenness) > 0 else 0.0
        std_v = float(np.std(versine)) if versine is not None and len(versine) > 0 else 0.0

        composite_error = (std_g * 1.2) + (std_c * 0.8) + (std_t * 2.0) + (std_u * 1.5) + (std_v * 1.2)
        return float(np.clip(100.0 - composite_error * 3.5, 0.0, 100.0))
