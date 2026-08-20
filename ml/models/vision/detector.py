# YOLOv8 wrapper with SAHI tiling and contract-compliant CalibratedSignal outputs (tc.v1).

from typing import List, Dict, Any, Optional, Tuple, Union
import os
from pathlib import Path
import numpy as np

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

from ml.core.schema import DefectClass, CalibratedSignal, SignalType
from ml.core.registry import register_model, ModelRegistry


CLASS_NAME_MAP: Dict[str, DefectClass] = {
    "missing_fastener": DefectClass.MISSING_FASTENER,
    "damaged_fastener": DefectClass.DAMAGED_FASTENER,
    "defective_clip": DefectClass.DAMAGED_FASTENER,
    "crack": DefectClass.CRACK,
    "rail_crack": DefectClass.CRACK,
    "spalling": DefectClass.SPALLING,
    "squat": DefectClass.SQUAT,
    "corrugation": DefectClass.CORRUGATION,
    "obstruction": DefectClass.OBSTRUCTION,
}


@register_model("yolov8_defect_detector")
class YOLOv8DefectDetector:
    """Production wrapper for YOLOv8 visual defect detection (what + where)."""

    def __init__(
        self,
        weights_path: Optional[Union[str, Path]] = None,
        confidence_threshold: float = 0.45,
        iou_threshold: float = 0.50,
        device: str = "cpu",
        use_sahi: bool = False,
        slice_size: Tuple[int, int] = (320, 320),
    ):
        self.conf_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.device = device
        self.use_sahi = use_sahi
        self.slice_size = slice_size
        self.model = None

        # Resolve weights from ModelRegistry if not explicitly provided
        if weights_path is None:
            # Check trained checkpoint first, then fallback to base weights
            trained_ckpt = ModelRegistry.get_trained_weights("vision", "yolo_rail_v0.1.pt")
            base_weights = ModelRegistry.get_base_weights("vision", "yolov8n.pt")
            if trained_ckpt.exists():
                weights_path = trained_ckpt
            elif base_weights.exists():
                weights_path = base_weights

        self.weights_path = str(weights_path) if weights_path else None
        if self.weights_path and os.path.exists(self.weights_path) and YOLO is not None:
            self.load_weights(self.weights_path)

    def load_weights(self, path: Union[str, Path]):
        """Load pretrained or fine-tuned YOLOv8 model weights (.pt or .onnx)."""
        if YOLO is None:
            raise RuntimeError("Ultralytics package is not installed.")
        self.weights_path = str(path)
        self.model = YOLO(self.weights_path)

    def predict(self, frame: np.ndarray) -> List[CalibratedSignal]:
        """
        Run object detection on an image frame and return contract-compliant CalibratedSignal items.
        Frame should be a HxWxC uint8 NumPy array (BGR or RGB).
        """
        signals: List[CalibratedSignal] = []

        if self.model is None:
            return signals

        h, w = frame.shape[:2]

        try:
            results = self.model.predict(
                source=frame,
                conf=self.conf_threshold,
                iou=self.iou_threshold,
                device=self.device,
                verbose=False,
            )
        except Exception:
            return signals

        if not results or len(results) == 0:
            return signals

        res = results[0]
        if res.boxes is None or len(res.boxes) == 0:
            return signals

        for box in res.boxes:
            cls_idx = int(box.cls[0])
            raw_cls_name = res.names.get(cls_idx, str(cls_idx)).lower()
            conf = float(box.conf[0])
            xyxy = box.xyxy[0].tolist()  # [x1, y1, x2, y2]

            defect_enum = CLASS_NAME_MAP.get(raw_cls_name, DefectClass.UNCLASSIFIED)

            signal = CalibratedSignal(
                stream_name="vision_detector",
                raw_score=conf,
                calibrated_prob=conf,  # will be scaled by TemperatureScaler downstream
                predicted_class=defect_enum,
                is_anomaly=True,
                signal_type=SignalType.VISUAL_KNOWN,
                threshold=self.conf_threshold,
                bbox=(float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])),
                explanation=f"YOLOv8 detected {raw_cls_name} with confidence {conf:.1%}",
                metadata={"raw_class": raw_cls_name, "box_xyxy": xyxy, "image_width": w, "image_height": h},
            )
            signals.append(signal)

        return signals

    def predict_sahi(
        self,
        frame: np.ndarray,
        slice_height: int = 320,
        slice_width: int = 320,
        overlap_ratio: float = 0.2,
    ) -> List[CalibratedSignal]:
        """
        Slicing Aided Hyper Inference (SAHI): slices high-res frames into overlapping tiles
        to detect millimeter-scale cracks and small fastener clips.
        """
        h, w = frame.shape[:2]
        step_y = int(slice_height * (1.0 - overlap_ratio))
        step_x = int(slice_width * (1.0 - overlap_ratio))

        all_signals: List[CalibratedSignal] = []

        for y in range(0, max(1, h - slice_height + 1), step_y):
            for x in range(0, max(1, w - slice_width + 1), step_x):
                tile = frame[y : y + slice_height, x : x + slice_width]
                tile_signals = self.predict(tile)

                # Offset bounding boxes back to global frame coordinates
                for sig in tile_signals:
                    if sig.bbox:
                        x1, y1, x2, y2 = sig.bbox
                        sig.bbox = (x1 + x, y1 + y, x2 + x, y2 + y)
                    if sig.metadata:
                        sig.metadata["image_width"] = w
                        sig.metadata["image_height"] = h
                    all_signals.append(sig)

        return all_signals
