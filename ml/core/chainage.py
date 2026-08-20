# Resample all sensor streams onto the common distance (chainage) axis.

from typing import Dict, List, Tuple
import numpy as np
from scipy.interpolate import interp1d
from ml.core.schema import ChainageWindow


class ChainageResampler:
    """Resamples asynchronous, time-based sensor streams onto a uniform distance grid."""

    def __init__(self, step_size_m: float = 0.25):
        self.step_size_m = step_size_m

    def resample_stream(
        self,
        distances: np.ndarray,
        values: np.ndarray,
        target_grid: np.ndarray,
    ) -> np.ndarray:
        """Interpolate a 1D or 2D array onto the target chainage grid."""
        if len(distances) < 2:
            return np.zeros_like(target_grid)
        
        # Sort if necessary
        sort_idx = np.argsort(distances)
        d_sorted = distances[sort_idx]
        v_sorted = values[sort_idx]

        # Linear interpolation with boundary clamping
        f = interp1d(d_sorted, v_sorted, bounds_error=False, fill_value="extrapolate")
        return f(target_grid)

    def slice_windows(
        self,
        start_chainage_m: float,
        end_chainage_m: float,
        window_len_m: float = 25.0,
        overlap_pct: float = 0.2,
    ) -> List[Tuple[float, float]]:
        """Compute window segments with specified overlap."""
        step = window_len_m * (1.0 - overlap_pct)
        windows = []
        curr = start_chainage_m
        while curr < end_chainage_m:
            w_end = min(curr + window_len_m, end_chainage_m)
            windows.append((curr, w_end))
            curr += step
            if w_end >= end_chainage_m:
                break
        return windows
