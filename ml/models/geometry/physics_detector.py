# Threshold detector on EN 13848 features for known geometry faults.

from typing import List, Optional
import numpy as np
from ml.core.schema import DefectClass, CalibratedSignal
from ml.core.registry import register_model


@register_model("physics_detector")
class EN13848PhysicsThresholdDetector:
    """Threshold-based fault detector enforcing EN 13848 Alert Limit (AL) and Immediate Action Limit (IAL)."""

    def __init__(
        self,
        gauge_ial_mm: float = 20.0,
        gauge_al_mm: float = 10.0,
        twist_ial_mm_per_m: float = 5.0,
        twist_al_mm_per_m: float = 3.0,
        cant_ial_mm: float = 160.0,
    ):
        self.gauge_ial = gauge_ial_mm
        self.gauge_al = gauge_al_mm
        self.twist_ial = twist_ial_mm_per_m
        self.twist_al = twist_al_mm_per_m
        self.cant_ial = cant_ial_mm

    def evaluate_window(
        self,
        gauge_dev_mm: np.ndarray,
        twist_mm_per_m: np.ndarray,
        cant_mm: np.ndarray,
    ) -> List[CalibratedSignal]:
        """Check if any physics feature crosses allowable limit thresholds."""
        signals = []

        max_gauge_dev = float(np.max(np.abs(gauge_dev_mm)))
        if max_gauge_dev > self.gauge_al:
            is_ial = max_gauge_dev > self.gauge_ial
            signals.append(
                CalibratedSignal(
                    stream_name="geometry_physics",
                    raw_score=max_gauge_dev,
                    calibrated_prob=0.95 if is_ial else 0.75,
                    predicted_class=DefectClass.GAUGE_WIDENING,
                    is_anomaly=True,
                    metadata={"severity": "critical" if is_ial else "high"},
                )
            )

        max_twist = float(np.max(np.abs(twist_mm_per_m)))
        if max_twist > self.twist_al:
            is_ial = max_twist > self.twist_ial
            signals.append(
                CalibratedSignal(
                    stream_name="geometry_physics",
                    raw_score=max_twist,
                    calibrated_prob=0.95 if is_ial else 0.75,
                    predicted_class=DefectClass.TWIST_EXCEEDANCE,
                    is_anomaly=True,
                    metadata={"severity": "critical" if is_ial else "high"},
                )
            )

        return signals
