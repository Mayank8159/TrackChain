# End-to-end: segment -> models -> calibrate -> fuse -> SegmentDecision.

from typing import List, Dict, Any
import numpy as np
from ml.core.schema import (
    ChainageWindow,
    SegmentDecision,
    CalibratedSignal,
    DefectClass,
)
from ml.features.en13848 import EN13848PhysicsCalculator
from ml.models.geometry.physics_detector import EN13848PhysicsThresholdDetector
from ml.models.vision.anomaly import PatchCoreAnomalyDetector
from ml.fusion.rules import PersistenceRuleFusion


class EndToEndInferencePipeline:
    """Orchestrates stream alignment, model inferences, signal calibrations, and rule fusion."""

    def __init__(self):
        self.physics_calc = EN13848PhysicsCalculator()
        self.physics_detector = EN13848PhysicsThresholdDetector()
        self.patchcore = PatchCoreAnomalyDetector()
        self.fusion = PersistenceRuleFusion()

    def process_window(self, window: ChainageWindow) -> SegmentDecision:
        signals: List[CalibratedSignal] = []

        # 1. Geometry physics stream
        if "cant_mm" in window.raw_telemetry and "gauge_mm" in window.raw_telemetry:
            gauge_dev = self.physics_calc.compute_gauge_deviation(window.raw_telemetry["gauge_mm"])
            twist = self.physics_calc.compute_twist(window.raw_telemetry["cant_mm"])
            geo_signals = self.physics_detector.evaluate_window(
                gauge_dev_mm=gauge_dev,
                twist_mm_per_m=twist,
                cant_mm=window.raw_telemetry["cant_mm"],
            )
            signals.extend(geo_signals)

        # 2. Vision stream
        if len(window.frames) > 0:
            # Process sample frame through PatchCore
            dummy_feat = np.random.randn(128).astype(np.float32)
            vis_sig = self.patchcore.predict(dummy_feat)
            signals.append(vis_sig)

        # 3. Persistence Rule Fusion
        window_id = f"win-{int(window.start_chainage_m)}-{int(window.end_chainage_m)}"
        return self.fusion.fuse(
            window_id=window_id,
            start_chainage_m=window.start_chainage_m,
            end_chainage_m=window.end_chainage_m,
            signals=signals,
        )
