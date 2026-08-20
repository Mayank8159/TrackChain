# Resample all sensor telemetry onto a uniform distance (chainage) spatial axis (tc.v1 SOTA).

from typing import Dict, List, Tuple, Optional, Union, Any
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d

from ml.core.schema import TrackSegment, ChainageWindow


@dataclass
class ResampledRun:
    """Container holding the complete resampled run and discretized track segments."""
    grid_chainage_m: np.ndarray
    resampled_telemetry: Dict[str, np.ndarray]
    segments: List[TrackSegment] = field(default_factory=list)


class ChainageResampler:
    """
    Resamples asynchronous, time-based sensor streams (IMU, Laser, Optical)
    onto a strictly uniform distance (chainage) grid.
    Filters out stationary train data to prevent spatial distortion and aliasing.
    """

    def __init__(
        self,
        step_size_m: float = 0.25,
        bin_size_m: Optional[float] = None,
        min_speed_mps: float = 0.20,
    ):
        self.step_size_m = bin_size_m if bin_size_m is not None else step_size_m
        self.bin_size_m = self.step_size_m
        self.min_speed_mps = min_speed_mps

    def compute_chainage_from_telemetry(
        self,
        timestamps_s: np.ndarray,
        speeds_mps: np.ndarray,
        start_chainage_m: float = 0.0,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute cumulative distance (chainage) via trapezoidal integration of velocity over time.
        Filters out intervals where the train is stationary (speed < min_speed_mps).

        Returns:
            valid_indices: boolean mask of non-stationary sample points
            chainage_m: cumulative distance array corresponding to valid points
        """
        if len(timestamps_s) < 2:
            return np.ones(len(timestamps_s), dtype=bool), np.array([start_chainage_m])

        dt = np.diff(timestamps_s)
        dt = np.maximum(dt, 0.0)

        avg_speed = (speeds_mps[:-1] + speeds_mps[1:]) / 2.0
        is_moving = avg_speed >= self.min_speed_mps

        # Incremental distance dx = v_avg * dt
        dx = np.where(is_moving, avg_speed * dt, 0.0)
        chainage = np.zeros(len(timestamps_s), dtype=np.float64)
        chainage[0] = start_chainage_m
        chainage[1:] = start_chainage_m + np.cumsum(dx)

        valid_mask = speeds_mps >= self.min_speed_mps
        if np.any(valid_mask):
            valid_mask[0] = True

        return valid_mask, chainage

    def resample_stream(
        self,
        distances: np.ndarray,
        values: np.ndarray,
        target_grid: np.ndarray,
    ) -> np.ndarray:
        """
        Interpolate a 1D signal onto the target chainage grid with boundary clamping.
        """
        if len(distances) < 2:
            return np.zeros_like(target_grid)

        sort_idx = np.argsort(distances)
        d_sorted = distances[sort_idx]
        v_sorted = values[sort_idx]

        unique_mask = np.concatenate(([True], np.diff(d_sorted) > 1e-6))
        d_unique = d_sorted[unique_mask]
        v_unique = v_sorted[unique_mask]

        if len(d_unique) < 2:
            return np.full_like(target_grid, v_sorted[0])

        f = interp1d(
            d_unique,
            v_unique,
            kind="linear",
            bounds_error=False,
            fill_value=(v_unique[0], v_unique[-1]),
        )
        return f(target_grid)

    def resample_telemetry_batch(
        self,
        timestamps_s: np.ndarray,
        speeds_mps: np.ndarray,
        sensor_streams: Dict[str, np.ndarray],
        start_chainage_m: float = 0.0,
    ) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
        """
        Takes raw telemetry time series and resamples all streams onto a uniform distance grid.

        Returns:
            grid_chainage_m: strictly uniform distance array (e.g. 0.0, 0.25, 0.50, ...)
            resampled_streams: dictionary of resampled sensor arrays
        """
        _, chainage = self.compute_chainage_from_telemetry(
            timestamps_s,
            speeds_mps,
            start_chainage_m=start_chainage_m,
        )

        total_distance = chainage[-1] - chainage[0]
        if total_distance <= self.step_size_m:
            grid = np.array([chainage[0], chainage[0] + self.step_size_m])
        else:
            grid = np.arange(chainage[0], chainage[-1] + (self.step_size_m * 0.5), self.step_size_m)

        resampled = {}
        for name, values in sensor_streams.items():
            resampled[name] = self.resample_stream(chainage, values, grid)

        return grid, resampled

    def process(
        self,
        telemetry_input: Union[pd.DataFrame, Dict[str, np.ndarray]],
        frames: Optional[List[Any]] = None,
        segment_length_m: float = 2.0,
        start_chainage_m: float = 0.0,
    ) -> ResampledRun:
        """
        End-to-end spatial processing:
          1. Resamples all sensor telemetry onto rigid 0.25m distance grid.
          2. Discretizes track run into standardized 2.0m TrackSegment objects.
          3. Distributes vision frames to their corresponding physical TrackSegments.
        """
        if isinstance(telemetry_input, pd.DataFrame):
            df = telemetry_input
            ts = df["timestamp"].values if "timestamp" in df else np.arange(len(df)) * 0.01
            speed = df["speed_mps"].values if "speed_mps" in df else np.full(len(df), 20.0)
            sensor_streams = {
                col: df[col].values
                for col in df.columns
                if col not in ("timestamp", "speed_mps")
            }
        else:
            sensor_streams = telemetry_input
            ts = sensor_streams.get("timestamp", np.arange(len(next(iter(sensor_streams.values())))) * 0.01)
            speed = sensor_streams.get("speed_mps", np.full(len(ts), 20.0))

        grid_m, resampled = self.resample_telemetry_batch(
            timestamps_s=ts,
            speeds_mps=speed,
            sensor_streams=sensor_streams,
            start_chainage_m=start_chainage_m,
        )

        frames_list = frames or []
        n_frames = len(frames_list)

        # Discretize into physical TrackSegments
        segments: List[TrackSegment] = []
        seg_start = grid_m[0]
        seg_id_counter = 0

        while seg_start < grid_m[-1]:
            seg_end = min(seg_start + segment_length_m, grid_m[-1])
            mask = (grid_m >= seg_start - 1e-4) & (grid_m <= seg_end + 1e-4)

            seg_telemetry = {k: v[mask] for k, v in resampled.items()}
            seg_telemetry["distances"] = grid_m[mask]

            # Assign frames that fall within this segment distance interval
            seg_frames = []
            if n_frames > 0:
                frame_distances = np.linspace(grid_m[0], grid_m[-1], n_frames)
                for f_idx, f_item in enumerate(frames_list):
                    if isinstance(f_item, tuple) and len(f_item) == 2 and isinstance(f_item[0], (int, float)):
                        f_pos, f_img = f_item
                        if (seg_start - 1e-3) <= f_pos <= (seg_end + 1e-3):
                            seg_frames.append(f_img)
                    else:
                        f_dist = frame_distances[f_idx]
                        if (seg_start - 1e-3) <= f_dist <= (seg_end + 1e-3):
                            seg_frames.append(f_item)

            segments.append(
                TrackSegment(
                    segment_id=f"seg_{seg_id_counter:04d}",
                    chainage_start_m=round(float(seg_start), 3),
                    chainage_end_m=round(float(seg_end), 3),
                    frames=seg_frames,
                    telemetry=seg_telemetry,
                )
            )

            seg_start += segment_length_m
            seg_id_counter += 1

        return ResampledRun(
            grid_chainage_m=grid_m,
            resampled_telemetry=resampled,
            segments=segments,
        )

    def slice_windows(
        self,
        start_chainage_m: float,
        end_chainage_m: float,
        window_len_m: float = 25.0,
        overlap_pct: float = 0.2,
    ) -> List[Tuple[float, float]]:
        """
        Compute overlapping track segment window bounds [start, end] across a track section.
        """
        step = window_len_m * (1.0 - overlap_pct)
        windows = []
        curr = start_chainage_m
        while curr < end_chainage_m:
            w_end = min(curr + window_len_m, end_chainage_m)
            windows.append((round(curr, 3), round(w_end, 3)))
            curr += step
            if w_end >= end_chainage_m:
                break
        return windows
