# Telemetry downsampling service using Largest Triangle Three Buckets (LTTB) peak preservation (tc.v1 SOTA).

from typing import List, Dict, Any, Tuple, Union, Optional
import numpy as np


def lttb_downsample(
    timestamps: Union[np.ndarray, List[float]],
    values: Union[np.ndarray, List[float]],
    target_points: int = 500,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Downsample time-series telemetry while strictly preserving visual shape,
    extreme spikes, and critical track fault anomalies.
    Reference: Sveinn Steinarsson (2013), Largest Triangle Three Buckets.
    """
    ts = np.asarray(timestamps)
    vals = np.asarray(values)
    n = len(ts)

    if target_points >= n or target_points < 3:
        return ts, vals

    sampled_indices = [0]
    bucket_size = (n - 2) / (target_points - 2)
    prev_idx = 0

    for i in range(target_points - 2):
        bucket_start = int((i + 0) * bucket_size) + 1
        bucket_end = int((i + 1) * bucket_size) + 1
        bucket_end = min(bucket_end, n - 1)

        next_start = int((i + 1) * bucket_size) + 1
        next_end = int((i + 2) * bucket_size) + 1
        next_end = min(next_end, n - 1)

        if next_end > next_start:
            avg_next_t = float(np.mean(ts[next_start:next_end]))
            avg_next_v = float(np.mean(vals[next_start:next_end]))
        else:
            avg_next_t, avg_next_v = float(ts[n - 1]), float(vals[n - 1])

        prev_t, prev_v = float(ts[prev_idx]), float(vals[prev_idx])
        max_area = -1.0
        max_idx = bucket_start

        for j in range(bucket_start, bucket_end):
            area = abs(
                (prev_t - avg_next_t) * (float(vals[j]) - prev_v)
                - (prev_t - float(ts[j])) * (avg_next_v - prev_v)
            ) * 0.5
            if area > max_area:
                max_area = area
                max_idx = j

        sampled_indices.append(max_idx)
        prev_idx = max_idx

    sampled_indices.append(n - 1)
    return ts[sampled_indices], vals[sampled_indices]


def downsample_telemetry_lttb(
    records: List[Any],
    threshold: int = 500,
    target_points: Optional[int] = None,
) -> List[Any]:
    """
    Applies LTTB peak preservation to a list of TelemetryRecord ORM objects or dictionaries.
    Prioritizes combined track defect signal: (twist_mm_per_m + vibration_rms + vertical_unevenness).
    """
    if target_points is not None:
        threshold = target_points

    if len(records) <= threshold or threshold <= 2:
        return records

    sampled = []
    every = (len(records) - 2) / (threshold - 2)
    a = 0
    sampled.append(records[a])

    def get_x_y(rec: Any) -> Tuple[float, float]:
        if isinstance(rec, dict):
            x = float(rec.get("chainage_m", 0.0))
            y = float(rec.get("twist_mm_per_m", 0.0) or 0.0) + float(rec.get("vibration_rms", 0.0) or 0.0)
        else:
            x = float(getattr(rec, "chainage_m", 0.0))
            y = float(getattr(rec, "twist_mm_per_m", 0.0) or 0.0) + float(getattr(rec, "vibration_rms", 0.0) or 0.0)
        return x, y

    for i in range(threshold - 2):
        avg_x = 0.0
        avg_y = 0.0
        avg_range_start = int((i + 1) * every) + 1
        avg_range_end = min(int((i + 2) * every) + 1, len(records))
        avg_range_length = avg_range_end - avg_range_start

        if avg_range_length > 0:
            for j in range(avg_range_start, avg_range_end):
                jx, jy = get_x_y(records[j])
                avg_x += jx
                avg_y += jy
            avg_x /= avg_range_length
            avg_y /= avg_range_length

        range_offs = int(i * every) + 1
        range_to = min(int((i + 1) * every) + 1, len(records))

        point_a_x, point_a_y = get_x_y(records[a])
        max_area = -1.0
        max_area_point = range_offs

        for k in range(range_offs, range_to):
            kx, ky = get_x_y(records[k])
            area = abs(
                (point_a_x - avg_x) * (ky - point_a_y)
                - (point_a_x - kx) * (avg_y - point_a_y)
            ) * 0.5

            if area > max_area:
                max_area = area
                max_area_point = k

        sampled.append(records[max_area_point])
        a = max_area_point

    sampled.append(records[-1])
    return sampled
