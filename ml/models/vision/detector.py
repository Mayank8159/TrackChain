# YOLOv8 wrapper with SAHI tiling, NMS merging, and contract-compliant CalibratedSignal outputs (tc.v1).

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


def nms_boxes(
    boxes: List[Tuple[float, float, float, float]],
    scores: List[float],
    iou_thresh: float = 0.50,
) -> List[int]:
    """Pure NumPy Non-Maximum Suppression for global coordinate deduplication."""
    if len(boxes) == 0:
        return []

    boxes_arr = np.array(boxes, dtype=np.float32)
    scores_arr = np.array(scores, dtype=np.float32)

    x1 = boxes_arr[:, 0]
    y1 = boxes_arr[:, 1]
    x2 = boxes_arr[:, 2]
    y2 = boxes_arr[:, 3]
    areas = np.maximum(0.0, x2 - x1) * np.maximum(0.0, y2 - y1)

    order = scores_arr.argsort()[::-1]
    keep = []

    while order.size > 0:
        i = order[0]
        keep.append(int(i))
        if order.size == 1:
            break

        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        inter = w * h
        union = areas[i] + areas[order[1:]] - inter
        ovr = inter / np.maximum(1e-6, union)

        inds = np.where(ovr <= iou_thresh)[0]
        order = order[inds + 1]

    return keep


@register_model("yolov8_defect_detector")
class YOLOv8DefectDetector:
    """Production wrapper for YOLOv8 visual defect detection (what + where)."""

    def __init__(
        self,
        weights_path: Optional[Union[str, Path]] = None,
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.60,
        device: str = "cpu",
        use_sahi: bool = False,
        slice_size: Tuple[int, int] = (480, 480),
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
            trained_ckpt = ModelRegistry.get_trained_weights("vision", "yolov8n_rail_best.pt")
            alias_ckpt = ModelRegistry.get_trained_weights("vision", "yolo_rail_v0.1.pt")
            base_weights = ModelRegistry.get_base_weights("vision", "yolov8n.pt")
            if trained_ckpt.exists():
                weights_path = trained_ckpt
            elif alias_ckpt.exists():
                weights_path = alias_ckpt
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
        if self.use_sahi:
            return self.predict_sahi(
                frame,
                slice_height=self.slice_size[0],
                slice_width=self.slice_size[1],
            )

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
        slice_height: int = 480,
        slice_width: int = 480,
        overlap_ratio: float = 0.2,
    ) -> List[CalibratedSignal]:
        """
        Slicing Aided Hyper Inference (SAHI): slices high-res frames into overlapping tiles
        to detect millimeter-scale cracks and small fastener clips, then merges overlapping
        bounding boxes via global NMS.
        """
        h, w = frame.shape[:2]
        step_y = int(slice_height * (1.0 - overlap_ratio))
        step_x = int(slice_width * (1.0 - overlap_ratio))

        raw_signals: List[CalibratedSignal] = []

        # Run detection on full image first for large objects / context
        full_signals = []
        if self.model is not None:
            try:
                full_res = self.model.predict(
                    source=frame,
                    conf=self.conf_threshold,
                    iou=self.iou_threshold,
                    device=self.device,
                    verbose=False,
                )
                if full_res and len(full_res) > 0 and full_res[0].boxes is not None:
                    res = full_res[0]
                    for box in res.boxes:
                        cls_idx = int(box.cls[0])
                        raw_cls_name = res.names.get(cls_idx, str(cls_idx)).lower()
                        conf = float(box.conf[0])
                        xyxy = box.xyxy[0].tolist()
                        defect_enum = CLASS_NAME_MAP.get(raw_cls_name, DefectClass.UNCLASSIFIED)
                        full_signals.append(
                            CalibratedSignal(
                                stream_name="vision_detector",
                                raw_score=conf,
                                calibrated_prob=conf,
                                predicted_class=defect_enum,
                                is_anomaly=True,
                                signal_type=SignalType.VISUAL_KNOWN,
                                threshold=self.conf_threshold,
                                bbox=(float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])),
                                explanation=f"YOLOv8 detected {raw_cls_name} with confidence {conf:.1%}",
                                metadata={"raw_class": raw_cls_name, "box_xyxy": xyxy, "image_width": w, "image_height": h, "sahi_tile": "full"},
                            )
                        )
            except Exception:
                pass

        raw_signals.extend(full_signals)

        # Slice frame into overlapping tiles
        y_starts = list(range(0, max(1, h - slice_height + 1), step_y))
        if y_starts and y_starts[-1] + slice_height < h:
            y_starts.append(h - slice_height)

        x_starts = list(range(0, max(1, w - slice_width + 1), step_x))
        if x_starts and x_starts[-1] + slice_width < w:
            x_starts.append(w - slice_width)

        for y in y_starts:
            for x in x_starts:
                tile = frame[y : y + slice_height, x : x + slice_width]
                if self.model is None:
                    continue
                try:
                    results = self.model.predict(
                        source=tile,
                        conf=self.conf_threshold,
                        iou=self.iou_threshold,
                        device=self.device,
                        verbose=False,
                    )
                except Exception:
                    continue

                if not results or len(results) == 0:
                    continue
                res = results[0]
                if res.boxes is None or len(res.boxes) == 0:
                    continue

                for box in res.boxes:
                    cls_idx = int(box.cls[0])
                    raw_cls_name = res.names.get(cls_idx, str(cls_idx)).lower()
                    conf = float(box.conf[0])
                    lx1, ly1, lx2, ly2 = box.xyxy[0].tolist()

                    gx1 = float(lx1 + x)
                    gy1 = float(ly1 + y)
                    gx2 = float(lx2 + x)
                    gy2 = float(ly2 + y)

                    defect_enum = CLASS_NAME_MAP.get(raw_cls_name, DefectClass.UNCLASSIFIED)
                    sig = CalibratedSignal(
                        stream_name="vision_detector",
                        raw_score=conf,
                        calibrated_prob=conf,
                        predicted_class=defect_enum,
                        is_anomaly=True,
                        signal_type=SignalType.VISUAL_KNOWN,
                        threshold=self.conf_threshold,
                        bbox=(gx1, gy1, gx2, gy2),
                        explanation=f"YOLOv8 SAHI detected {raw_cls_name} with confidence {conf:.1%}",
                        metadata={"raw_class": raw_cls_name, "box_xyxy": [gx1, gy1, gx2, gy2], "image_width": w, "image_height": h, "sahi_tile": f"({x},{y})"},
                    )
                    raw_signals.append(sig)

        if not raw_signals:
            return []

        # Deduplicate signals across tile boundaries using NMS per defect class
        final_signals: List[CalibratedSignal] = []
        classes_present = set(s.predicted_class for s in raw_signals)

        for c_enum in classes_present:
            class_signals = [s for s in raw_signals if s.predicted_class == c_enum and s.bbox is not None]
            if not class_signals:
                continue

            boxes = [s.bbox for s in class_signals]
            scores = [s.raw_score for s in class_signals]
            keep_indices = nms_boxes(boxes, scores, iou_thresh=self.iou_threshold)

            for idx in keep_indices:
                final_signals.append(class_signals[idx])

        return final_signals
