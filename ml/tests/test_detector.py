# Unit tests for YOLOv8 visual defect detector (tc.v1).

import pytest
import numpy as np
from ml.models.vision.detector import YOLOv8DefectDetector, CLASS_NAME_MAP
from ml.core.schema import DefectClass, SignalType, CalibratedSignal


def test_yolo_detector_initialization():
    # When initialized with auto-discovery from registry
    detector = YOLOv8DefectDetector(confidence_threshold=0.55, iou_threshold=0.45)
    assert detector.conf_threshold == 0.55
    assert detector.iou_threshold == 0.45
    assert detector.device == "cpu"
    assert detector.model is not None


def test_yolo_detector_predict_uninitialized():
    # Explicitly uninitialized
    detector = YOLOv8DefectDetector(weights_path="")
    assert detector.model is None
    frame = np.zeros((640, 640, 3), dtype=np.uint8)
    signals = detector.predict(frame)
    assert isinstance(signals, list)
    assert len(signals) == 0


def test_yolo_detector_class_mappings():
    assert CLASS_NAME_MAP["missing_fastener"] == DefectClass.MISSING_FASTENER
    assert CLASS_NAME_MAP["crack"] == DefectClass.CRACK
    assert CLASS_NAME_MAP["spalling"] == DefectClass.SPALLING
    assert CLASS_NAME_MAP["obstruction"] == DefectClass.OBSTRUCTION


def test_yolo_detector_sahi_tiling_logic(monkeypatch):
    detector = YOLOv8DefectDetector(weights_path="")

    # Mock predict method on detector to return a synthetic signal on a tile
    def mock_predict(tile: np.ndarray):
        return [
            CalibratedSignal(
                stream_name="vision_detector",
                raw_score=0.91,
                calibrated_prob=0.91,
                predicted_class=DefectClass.MISSING_FASTENER,
                is_anomaly=True,
                signal_type=SignalType.VISUAL_KNOWN,
                threshold=0.5,
                bbox=(10.0, 15.0, 50.0, 55.0),
                explanation="Mock fastener detection",
            )
        ]

    monkeypatch.setattr(detector, "predict", mock_predict)

    # 1280x1280 image sliced into 640x640 tiles
    frame = np.zeros((1280, 1280, 3), dtype=np.uint8)
    sahi_signals = detector.predict_sahi(frame, slice_height=640, slice_width=640, overlap_ratio=0.2)

    assert len(sahi_signals) > 0
    # Check that later tiles have offset coordinates > 0
    bboxes = [s.bbox for s in sahi_signals if s.bbox is not None]
    max_x = max(b[0] for b in bboxes)
    assert max_x > 0.0


def test_calibrated_signal_to_backend_dict():
    sig = CalibratedSignal(
        stream_name="yolo_v8_detector",
        raw_score=0.94,
        calibrated_prob=0.92,
        predicted_class=DefectClass.MISSING_FASTENER,
        is_anomaly=True,
        signal_type=SignalType.VISUAL_KNOWN,
        threshold=0.5,
        bbox=(120.0, 450.0, 180.0, 510.0),
        explanation="Missing rail clip detected",
        metadata={"image_width": 640, "image_height": 640},
    )

    # Ensure format matches backend MLSignalCreate
    payload_dict = {
        "model_name": sig.stream_name,
        "model_version": "0.1.0",
        "signal_type": sig.signal_type.value,
        "raw_score": sig.raw_score,
        "calibrated_score": sig.calibrated_prob,
        "threshold": sig.threshold,
        "fired": sig.is_anomaly,
        "label": sig.predicted_class.value if sig.predicted_class else None,
        "bbox": list(sig.bbox) if sig.bbox else None,
        "explanation": sig.explanation,
    }

    assert payload_dict["label"] == "missing_fastener"
    assert payload_dict["raw_score"] == 0.94
    assert len(payload_dict["bbox"]) == 4
