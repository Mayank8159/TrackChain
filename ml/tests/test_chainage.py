# Unit tests for distance resampling and alignment.

import numpy as np
from ml.core.chainage import ChainageResampler


def test_chainage_resampling():
    resampler = ChainageResampler(step_size_m=1.0)
    distances = np.array([0.0, 2.0, 4.0])
    values = np.array([10.0, 20.0, 30.0])

    target_grid = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
    resampled = resampler.resample_stream(distances, values, target_grid)

    assert len(resampled) == 5
    assert np.isclose(resampled[1], 15.0)  # midpoint between 10 and 20


def test_slice_windows():
    resampler = ChainageResampler()
    windows = resampler.slice_windows(start_chainage_m=0.0, end_chainage_m=100.0, window_len_m=25.0, overlap_pct=0.0)
    assert len(windows) == 4
    assert windows[0] == (0.0, 25.0)
    assert windows[-1] == (75.0, 100.0)
