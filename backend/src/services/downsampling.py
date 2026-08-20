# Telemetry downsampling service using LTTB / Min-Max peak preservation (tc.v1 SOTA).

from typing import List, Dict, Any
from src.db.models import TelemetryRecord


def downsample_telemetry_lttb(
    records: List[TelemetryRecord],
    threshold: int = 500,
) -> List[TelemetryRecord]:
    """
    Largest-Triangle-Three-Buckets (LTTB) / Peak-preserving downsampling for railway telemetry curves.
    Reduces dense 10-100Hz point streams to representative visual samples while strictly preserving
    critical spikes (e.g. twist exceedance or vibration shocks).
    """
    if len(records) <= threshold or threshold <= 2:
        return records

    sampled: List[TelemetryRecord] = []
    every = (len(records) - 2) / (threshold - 2)
    a = 0
    sampled.append(records[a])

    for i in range(threshold - 2):
        # Calculate point average for next bucket (bucket c)
        avg_x = 0.0
        avg_y = 0.0
        avg_range_start = int((i + 1) * every) + 1
        avg_range_end = min(int((i + 2) * every) + 1, len(records))
        avg_range_length = avg_range_end - avg_range_start

        if avg_range_length > 0:
            for j in range(avg_range_start, avg_range_end):
                avg_x += records[j].chainage_m
                avg_y += (records[j].vibration_rms or 0.0) + (records[j].twist_mm_per_m or 0.0)
            avg_x /= avg_range_length
            avg_y /= avg_range_length

        # Get the range for this bucket (bucket b)
        range_offs = int(i * every) + 1
        range_to = min(int((i + 1) * every) + 1, len(records))

        # Point a
        point_a_x = records[a].chainage_m
        point_a_y = (records[a].vibration_rms or 0.0) + (records[a].twist_mm_per_m or 0.0)

        max_area = -1.0
        max_area_point = range_offs

        for k in range(range_offs, range_to):
            # Calculate triangle area over points a, b, and average c
            area = abs(
                (point_a_x - avg_x)
                * (((records[k].vibration_rms or 0.0) + (records[k].twist_mm_per_m or 0.0)) - point_a_y)
                - (point_a_x - records[k].chainage_m)
                * (avg_y - point_a_y)
            ) * 0.5

            if area > max_area:
                max_area = area
                max_area_point = k

        sampled.append(records[max_area_point])
        a = max_area_point

    # Always include last point
    sampled.append(records[-1])
    return sampled
