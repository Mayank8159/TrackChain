# Unit tests for deterministic EN 13848 & RDSO geometry feature math (tc.v1 SOTA).

import pytest
import numpy as np
from ml.features.en13848 import EN13848PhysicsCalculator


def test_gauge_deviation():
    calc = EN13848PhysicsCalculator(nominal_gauge_mm=1676.0)
    measured = np.array([1676.0, 1679.0, 1682.0, 1673.0])
    dev = calc.compute_gauge_deviation(measured)
    assert np.allclose(dev, np.array([0.0, 3.0, 6.0, -3.0]))


def test_cross_level_and_twist():
    calc = EN13848PhysicsCalculator(nominal_gauge_mm=1676.0)
    # Roll in radians corresponding to 10mm cant
    roll = np.arcsin(10.0 / 1676.0)
    roll_arr = np.zeros(40)
    # Step change in cant at index 20 (corresponding to 5.0m with 0.25m step)
    roll_arr[20:] = roll

    cant = calc.compute_cross_level(roll_arr)
    assert np.isclose(cant[20], 10.0)

    # 3m base twist (12 samples of 0.25m)
    twist_3m = calc.compute_twist(cant, base_length_m=3.0, step_m=0.25)
    assert np.isclose(twist_3m[20], 10.0)  # full step change
    assert np.isclose(twist_3m[35], 0.0)   # constant cant after step


def test_chord_versine_and_curvature():
    calc = EN13848PhysicsCalculator(nominal_gauge_mm=1676.0)
    # 200m track section with a 10m localized bump of 8mm
    step_m = 0.25
    x = np.arange(0, 100, step_m)
    lateral_pos = np.zeros_like(x)
    # Localized bump at x = 50m (span 45m to 55m)
    bump_mask = (x >= 45.0) & (x <= 55.0)
    lateral_pos[bump_mask] = 8.0 * np.sin(np.pi * (x[bump_mask] - 45.0) / 10.0)

    versine_10m = calc.compute_chord_versine(lateral_pos, chord_length_m=10.0, step_m=step_m, filter_curvature=False)
    
    # Max versine should peak at the center of the bump
    center_idx = int(50.0 / step_m)
    assert versine_10m[center_idx] > 5.0


def test_track_quality_index():
    calc = EN13848PhysicsCalculator()
    
    # Perfect track (zero variance)
    n = 100
    perfect_tqi = calc.compute_track_quality_index(
        gauge_dev=np.zeros(n),
        cant=np.zeros(n),
        twist=np.zeros(n),
        unevenness=np.zeros(n),
    )
    assert perfect_tqi == 100.0

    # Degraded track (high variance)
    degraded_tqi = calc.compute_track_quality_index(
        gauge_dev=np.random.normal(0, 4.0, n),
        cant=np.random.normal(0, 6.0, n),
        twist=np.random.normal(0, 3.0, n),
        unevenness=np.random.normal(0, 5.0, n),
    )
    assert degraded_tqi < 80.0


def test_compute_all_features():
    calc = EN13848PhysicsCalculator()
    n = 200
    roll = np.zeros(n)
    lateral = np.zeros(n)
    vertical = np.zeros(n)
    gauge = np.full(n, 1676.0)

    feats = calc.compute_all_features(roll, lateral, vertical, gauge, step_m=0.25)
    assert "cant_mm" in feats
    assert "twist_3m_mm" in feats
    assert "versine_10m_mm" in feats
    assert "unevenness_10m_mm" in feats
    assert "gauge_dev_mm" in feats
    assert "tqi" in feats
    assert feats["tqi"] == 100.0
