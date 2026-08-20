# Unit tests for calibration routines.

import numpy as np
from ml.calibration.fpr_threshold import FPRThresholdCalibrator


def test_fpr_threshold_calibrator():
    calibrator = FPRThresholdCalibrator(target_fpr=0.05)
    # Generate 100 uniform samples from 0 to 1
    scores = np.linspace(0, 1, 101)
    thresh = calibrator.fit(scores)
    assert 0.90 <= thresh <= 1.0
    assert calibrator.is_anomaly(0.98) is True
    assert calibrator.is_anomaly(0.50) is False
