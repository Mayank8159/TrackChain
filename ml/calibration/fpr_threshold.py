# Set anomaly-score operating thresholds at a target false-positive rate.

from typing import Dict
import numpy as np


class FPRThresholdCalibrator:
    """Computes operating thresholds for continuous anomaly scores constrained to a target false-positive rate budget."""

    def __init__(self, target_fpr: float = 0.01):
        self.target_fpr = target_fpr
        self.threshold: float = 0.5

    def fit(self, normal_scores: np.ndarray) -> float:
        """Find the score percentile such that FPR <= target_fpr on nominal data."""
        if len(normal_scores) == 0:
            return self.threshold

        percentile = (1.0 - self.target_fpr) * 100.0
        self.threshold = float(np.percentile(normal_scores, percentile))
        return self.threshold

    def is_anomaly(self, score: float) -> bool:
        return score >= self.threshold

    def score_to_prob(self, score: float) -> float:
        """Map raw score to a normalized [0, 1] probability relative to threshold."""
        ratio = score / max(self.threshold, 1e-6)
        # Sigmoid centered at threshold
        return float(1.0 / (1.0 + np.exp(-3.0 * (ratio - 1.0))))
