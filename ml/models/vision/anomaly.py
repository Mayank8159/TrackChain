# PatchCore normal-only anomaly detector for novel surface defects.

from typing import Optional
import numpy as np
import torch
import torch.nn as nn
from ml.core.schema import DefectClass, CalibratedSignal
from ml.core.registry import register_model


@register_model("patchcore_anomaly_detector")
class PatchCoreAnomalyDetector:
    """PatchCore normal-only visual anomaly detector using greedy coreset subsampling."""

    def __init__(
        self,
        backbone: str = "wide_resnet50_2",
        coreset_sampling_ratio: float = 0.01,
        threshold: float = 0.5,
    ):
        self.backbone_name = backbone
        self.coreset_ratio = coreset_sampling_ratio
        self.threshold = threshold
        self.memory_bank: Optional[np.ndarray] = None

    def fit(self, normal_features: np.ndarray):
        """Fit memory bank on normal-only rail surface patch features."""
        # Perform random or k-center greedy coreset reduction
        n_samples = max(1, int(len(normal_features) * self.coreset_ratio))
        indices = np.random.choice(len(normal_features), n_samples, replace=False)
        self.memory_bank = normal_features[indices]

    def predict(self, feature_vector: np.ndarray) -> CalibratedSignal:
        """Compute nearest-neighbor anomaly score against memory bank."""
        if self.memory_bank is None:
            # Return nominal default
            return CalibratedSignal(
                stream_name="vision_anomaly",
                raw_score=0.05,
                calibrated_prob=0.05,
                predicted_class=None,
                is_anomaly=False,
            )

        # Euclidean distance to closest normal embedding
        dists = np.linalg.norm(self.memory_bank - feature_vector, axis=1)
        min_dist = float(np.min(dists))
        is_anom = min_dist > self.threshold

        return CalibratedSignal(
            stream_name="vision_anomaly",
            raw_score=min_dist,
            calibrated_prob=min_dist / (min_dist + 1.0),
            predicted_class=DefectClass.UNCLASSIFIED if is_anom else None,
            is_anomaly=is_anom,
        )
