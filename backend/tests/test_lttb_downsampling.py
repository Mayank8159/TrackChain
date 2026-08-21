# Tests for Largest Triangle Three Buckets (LTTB) peak-preserving downsampling algorithm (tc.v1 SOTA).

import numpy as np
import pytest
from src.services.downsampling import lttb_downsample, downsample_telemetry_lttb


def test_lttb_downsample_peak_preservation():
    # Create 1000 points with an extreme fault spike at index 500
    n = 1000
    timestamps = np.linspace(0, 100, n)
    values = np.sin(timestamps) * 0.5
    # Inject 10x critical twist spike
    values[500] = 8.5

    target_points = 50
    down_t, down_v = lttb_downsample(timestamps, values, target_points=target_points)

    assert len(down_t) == target_points
    assert len(down_v) == target_points

    # Verify first and last point are retained
    assert down_t[0] == timestamps[0]
    assert down_t[-1] == timestamps[-1]

    # Verify the extreme peak (8.5) was preserved by the triangle area maximizer
    assert np.max(down_v) == pytest.approx(8.5, abs=0.01)


def test_downsample_telemetry_lttb_dict_records():
    records = []
    for i in range(100):
        records.append({
            "chainage_m": float(i * 5),
            "twist_mm_per_m": 12.0 if i == 45 else 0.4,
            "vibration_rms": 0.2,
        })

    sampled = downsample_telemetry_lttb(records, threshold=20)
    assert len(sampled) == 20

    # Ensure peak at 45 (chainage 225m) is in sampled points
    peak_found = any(r["twist_mm_per_m"] == 12.0 for r in sampled)
    assert peak_found is True
