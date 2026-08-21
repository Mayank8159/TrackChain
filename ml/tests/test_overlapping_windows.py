"""
ml/tests/test_overlapping_windows.py
Validates Overlapping Window Extraction (50% overlap) and boundary defect protection.
"""

import pytest
import numpy as np

from ml.inference.pipeline import extract_overlapping_windows


def test_extract_overlapping_windows_stride_and_count():
    """Verify that a 160-bin track window produces overlapping slices with 50% stride (40 bins)."""
    n_bins = 160
    window_size = 80
    overlap = 0.5  # stride = 40

    features = {
        "cant_mm": np.arange(n_bins, dtype=np.float32),
        "twist_3m_mm": np.zeros(n_bins, dtype=np.float32),
    }

    windows, positions = extract_overlapping_windows(features, window_size=window_size, overlap=overlap)

    # 0..80, 40..120, 80..160 -> 3 windows
    assert len(windows) == 3
    assert positions == [0, 40, 80]
    for w in windows:
        assert len(w["cant_mm"]) == window_size


def test_overlapping_window_boundary_defect_preservation():
    """
    Verify that a defect located right on a standard 80-bin boundary (bin 75 to 85)
    is cleanly centered and preserved in the overlapping middle window.
    """
    n_bins = 160
    window_size = 80
    features = {
        "unevenness_10m_mm": np.zeros(n_bins, dtype=np.float32),
    }
    # Injected defect centered at bin 80 (split in non-overlapping 0..80 and 80..160)
    features["unevenness_10m_mm"][75:85] = 12.0

    windows, positions = extract_overlapping_windows(features, window_size=80, overlap=0.5)

    # Window 0: contains only [75:80] (half defect)
    # Window 1 (starts at 40): contains [75:85] fully inside window (bins 35:45)!
    mid_win = windows[1]["unevenness_10m_mm"]
    assert np.max(mid_win) == 12.0
    assert np.count_nonzero(mid_win == 12.0) == 10
