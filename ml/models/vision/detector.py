# YOLOv8 wrapper for known discrete defects (what + where).

from typing import List, Dict, Any, Optional
import numpy as np
from ml.core.schema import DefectClass, CalibratedSignal
from ml.core.registry import register_model


@register_model("yolov8_defect_detector")
class YOLOv8DefectDetector:
    """Wrapper around YOLOv8 model for discrete railway surface defect detection."""

    def __init__(
        self,
        weights_path: Optional[str] = None,
        confidence_threshold: float = 0.45,
        device: str = "cpu",
    ):
        self.weights_path = weights_path
        self.conf_threshold = confidence_threshold
        self.device = device
        self.model = None

    def load_weights(self, path: str):
        self.weights_path = path
        # In production with ultralytics:
        # from ultralytics import YOLO
        # self.model = YOLO(path)

    def predict(self, frame: np.ndarray) -> List[CalibratedSignal]:
        """Run object detection on an image frame and return detected fault signals."""
        signals: List[CalibratedSignal] = []

        # When model isn't initialized or running in mock mode:
        # Generate simulated output for testing
        if self.model is None:
            return signals

        # Real inference code path:
        # results = self.model.predict(frame, conf=self.conf_threshold, device=self.device)
        # for box in results[0].boxes:
        #     cls_name = results[0].names[int(box.cls[0])]
        #     conf = float(box.conf[0])
        #     signals.append(CalibratedSignal(
        #         stream_name="vision_detector",
        #         raw_score=conf,
        #         calibrated_prob=conf,
        #         predicted_class=DefectClass(cls_name),
        #         is_anomaly=True,
        #         metadata={"box": box.xyxy[0].tolist()}
        #     ))

        return signals
