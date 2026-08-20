# Fit calibration for all models and persist to artifacts/calibration.

import os
import json
import numpy as np
from ml.calibration.temperature import TemperatureScaler
from ml.calibration.fpr_threshold import FPRThresholdCalibrator
from ml.utils.logging import get_ml_logger

logger = get_ml_logger("calibrate")


def main():
    logger.info("Fitting post-processing calibration parameters...")
    os.makedirs("artifacts/calibration", exist_ok=True)

    # 1. Temperature scaling
    val_logits = np.random.randn(200, 4)
    val_labels = np.random.randint(0, 4, 200)
    scaler = TemperatureScaler()
    T = scaler.fit(val_logits, val_labels)
    logger.info(f"Fitted Temperature Scaling parameter: T = {T:.4f}")

    # 2. FPR threshold calibration
    normal_scores = np.random.exponential(0.2, 1000)
    fpr_cal = FPRThresholdCalibrator(target_fpr=0.01)
    thresh = fpr_cal.fit(normal_scores)
    logger.info(f"Fitted 1% FPR Anomaly Threshold: {thresh:.4f}")

    cal_params = {
        "temperature": float(T),
        "anomaly_threshold_1pct_fpr": float(thresh),
    }
    with open("artifacts/calibration/params.json", "w") as f:
        json.dump(cal_params, f, indent=2)

    logger.info("Persisted calibration params to artifacts/calibration/params.json")


if __name__ == "__main__":
    main()
