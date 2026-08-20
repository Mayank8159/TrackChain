# End-to-end: segment -> models -> calibrate -> fuse -> SegmentDecision (tc.v1 SOTA).

from typing import List, Dict, Any, Optional
import numpy as np
from ml.core.schema import (
    ChainageWindow,
    SegmentDecision,
    CalibratedSignal,
    DefectClass,
    SignalType,
)
from ml.features.en13848 import EN13848PhysicsCalculator
from ml.models.geometry.physics_detector import EN13848PhysicsThresholdDetector
from ml.models.vision.detector import YOLOv8DefectDetector
from ml.models.vision.anomaly import PatchCoreAnomalyDetector
from ml.fusion.rules import PersistenceRuleFusion


class EndToEndInferencePipeline:
    """
    Orchestrates the Core Sensor Fusion Triad:
      1. YOLOv8 Visual Defect Detector (Phase 2.1 - VISUAL_KNOWN)
      2. PatchCore Visual Anomaly Detector (Phase 2.2 - VISUAL_NOVEL)
      3. EN 13848 / RDSO Geometry Physics (Phase 2.3 - GEOMETRY_KNOWN)
    Followed by multi-modal signal fusion and persistence logic.
    """

    def __init__(
        self,
        yolo_detector: Optional[YOLOv8DefectDetector] = None,
        patchcore_detector: Optional[PatchCoreAnomalyDetector] = None,
        physics_calculator: Optional[EN13848PhysicsCalculator] = None,
        physics_detector: Optional[EN13848PhysicsThresholdDetector] = None,
        fusion_engine: Optional[PersistenceRuleFusion] = None,
    ):
        self.yolo = yolo_detector or YOLOv8DefectDetector()
        self.patchcore = patchcore_detector or PatchCoreAnomalyDetector()
        self.physics_calc = physics_calculator or EN13848PhysicsCalculator(nominal_gauge_mm=1676.0)
        self.physics_detector = physics_detector or EN13848PhysicsThresholdDetector()
        self.fusion = fusion_engine or PersistenceRuleFusion()

    def process_window(self, window: ChainageWindow) -> SegmentDecision:
        """Process a physical track segment through all streams and fuse decisions."""
        signals: List[CalibratedSignal] = []

        # 1. Vision Stream (YOLOv8 + PatchCore)
        if window.frames and len(window.frames) > 0:
            for frame in window.frames:
                # 1A. YOLOv8 for known defects (fasteners, cracks)
                yolo_sigs = self.yolo.predict(frame)
                signals.extend(yolo_sigs)

                # 1B. PatchCore for novel surface anomalies
                patch_sigs = self.patchcore.predict(frame)
                signals.extend(patch_sigs)

        # 2. Geometry Physics Stream (RDSO / EN 13848 Multi-Chord Math)
        telemetry = window.raw_telemetry or {}
        n_samples = len(window.distances) if window.distances is not None else 0

        if n_samples > 0:
            # Extract or default telemetry channels
            roll_rad = telemetry.get("roll_rad", np.zeros(n_samples))
            lateral_mm = telemetry.get("lateral_pos_mm", telemetry.get("ay", np.zeros(n_samples)))
            vertical_mm = telemetry.get("vertical_pos_mm", telemetry.get("az", np.zeros(n_samples)))
            gauge_mm = telemetry.get("gauge_mm", np.full(n_samples, self.physics_calc.nominal_gauge))

            step_m = 0.25
            if len(window.distances) > 1:
                step_m = float(np.mean(np.diff(window.distances)))

            # Compute complete feature suite
            geom_features = self.physics_calc.compute_all_features(
                roll_rad=roll_rad,
                lateral_pos_mm=lateral_mm,
                vertical_pos_mm=vertical_mm,
                gauge_mm=gauge_mm,
                step_m=step_m,
            )

            # Evaluate against deterministic thresholds
            geo_signals = self.physics_detector.evaluate_features(geom_features)
            signals.extend(geo_signals)

        # 3. Persistence Rule Fusion
        window_id = f"win-{int(window.start_chainage_m):05d}-{int(window.end_chainage_m):05d}"
        return self.fusion.fuse(
            window_id=window_id,
            start_chainage_m=window.start_chainage_m,
            end_chainage_m=window.end_chainage_m,
            signals=signals,
        )
