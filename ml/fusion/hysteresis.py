"""
ml/fusion/hysteresis.py
Exponential Decay Spatial Hysteresis for Noise-Resistant Novel Anomaly Persistence (tc.v1 SOTA).
"""

from typing import Optional


class ExponentialHysteresis:
    """
    Maintains a decaying evidence accumulation score across sequential track segments.
    Prevents single isolated sensor spikes from alarming while allowing genuine defects
    persisting across consecutive windows to trigger and maintain confirmed alert states.
    """

    def __init__(self, decay_rate: float = 0.7, threshold: float = 0.5, alpha: float = 0.3):
        self.decay_rate = float(decay_rate)
        self.threshold = float(threshold)
        self.alpha = float(alpha)
        self.accumulated_score = 0.0

    def reset(self):
        """Reset accumulated evidence."""
        self.accumulated_score = 0.0

    def update(self, current_fired: bool, current_confidence: float) -> bool:
        """
        Updates accumulated score:
          - If fired: accumulated_score = (decay_rate * accumulated_score) + (alpha * current_confidence)
          - If not fired: accumulated_score = accumulated_score * decay_rate
        Returns True if accumulated_score >= threshold.
        """
        if current_fired:
            self.accumulated_score = (self.decay_rate * self.accumulated_score) + (self.alpha * current_confidence)
        else:
            self.accumulated_score *= self.decay_rate

        return self.accumulated_score >= self.threshold

    def get_score(self) -> float:
        return float(self.accumulated_score)
