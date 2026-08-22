"""TrackChain ML Evaluation Core.
SINGLE SOURCE OF TRUTH for artifact paths and model wrappers.
If a constructor/method signature differs in your repo, edit ONLY this file.
"""
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "artifacts"

CFG = {
    "yolo_onnx":  ART / "exports" / "yolov8n_rail_best_int8.onnx",
    "patchcore":  ART / "checkpoints" / "vision" / "patchcore_memory_bank.npz",
    "yolo_temp":  ART / "calibration" / "yolo_temp.json",
    "pc_calib":   ART / "calibration" / "patchcore_calibration.json",
    "fusion_thr": 0.5,
}

def _read_img(path):
    from PIL import Image
    return np.array(Image.open(path).convert("RGB"))

# ---------------- YOLO (Tier A) ----------------
class YOLOAdapter:
    def __init__(self):
        from ml.models.vision.detector import YOLOv8DefectDetector as Det
        self.m = Det(str(CFG["yolo_onnx"]))

    def detect(self, img):
        # YOLOv8DefectDetector.predict() returns List[CalibratedSignal]
        signals = self.m.predict(img)
        return self._norm(signals)

    @staticmethod
    def _norm(signals):
        """Normalize List[CalibratedSignal] → (boxes, scores)."""
        if not signals:
            return [], []
        boxes, scores = [], []
        for s in signals:
            conf = float(getattr(s, "raw_score", getattr(s, "calibrated_prob", 0.0)))
            bbox = getattr(s, "bbox", None)
            if bbox is not None:
                boxes.append(list(bbox))
                scores.append(conf)
        return boxes, scores

# ---------------- PatchCore (Tier B) ----------------
class PatchCoreAdapter:
    # Measured from real data: clean=27.66, known=29.95, novel=38.02
    # We normalize raw_dist to [0,1] where 25.0 = 0.0, 40.0 = 1.0
    _DIST_MIN = 25.0
    _DIST_MAX = 40.0

    def __init__(self):
        from ml.models.vision.anomaly import PatchCoreAnomalyDetector as PC
        self.m = PC(checkpoint_path=str(CFG["patchcore"]))

    def score(self, img) -> float:
        """Returns anomaly score [0,1] normalized from measured distance range."""
        # predict_raw() returns (max_distance: float, anomaly_map: ndarray)
        raw_dist, _ = self.m.predict_raw(img)
        # Clamp and normalize to [0,1] using empirically measured range
        score = (float(raw_dist) - self._DIST_MIN) / (self._DIST_MAX - self._DIST_MIN)
        return max(0.0, min(1.0, score))

# ---------------- Hough (OPTIONAL, non-load-bearing) ----------------
def load_hough():
    try:
        from ml.models.vision.hough_geometry import HoughGeometryExtractor as H
        return H()
    except Exception as e:
        print(f"   [Hough CV] optional extractor unavailable ({type(e).__name__}) — bonus stage skipped")
        return None

# ---------------- Fusion (camera-only safe) ----------------
class FusionAdapter:
    def __init__(self, threshold=None):
        from ml.fusion.rules import TrackChainFusionEngine as FE
        self.m = FE()
        self._thr = threshold or CFG["fusion_thr"]

    def decide(self, yolo_cal, pc_cal):
        """Build CalibratedSignal list and call TrackChainFusionEngine.fuse()."""
        from ml.core.schema import CalibratedSignal, SignalType, DefectClass
        import time
        signals = []
        if yolo_cal > 0.0:
            signals.append(CalibratedSignal(
                stream_name="yolo_detector",
                raw_score=yolo_cal, calibrated_prob=yolo_cal,
                predicted_class=DefectClass.MISSING_FASTENER,
                is_anomaly=True, signal_type=SignalType.VISUAL_KNOWN,
                threshold=self._thr,
            ))
        if pc_cal > self._thr:
            signals.append(CalibratedSignal(
                stream_name="patchcore",
                raw_score=pc_cal, calibrated_prob=pc_cal,
                predicted_class=DefectClass.UNCLASSIFIED,
                is_anomaly=True, signal_type=SignalType.VISUAL_NOVEL,
                threshold=self._thr,
            ))
        decision = self.m.fuse(signals)
        return self._norm(decision)

    @staticmethod
    def _norm(d):
        if hasattr(d, "verdict"):
            return str(d.verdict), float(getattr(d, "confidence", 0.5))
        if hasattr(d, "decision"):
            return str(d.decision), float(getattr(d, "confidence", 0.5))
        if isinstance(d, dict):
            return str(d.get("verdict", d.get("decision", "OK"))), float(d.get("confidence", 0.5))
        return str(d), 0.5

# ---------------- Calibration (optional, graceful) ----------------
def calibrate_yolo(raw):
    try:
        from ml.calibration.temperature import TemperatureScaler
        return float(TemperatureScaler.load(str(CFG["yolo_temp"])).scale(raw))
    except Exception:
        return float(raw)

def norm_decision_name(verdict):
    v = str(verdict).upper().split(".")[-1] # handle Enums like SegmentDecision.INSPECT
    return "INSPECT" if v in ("INSPECT", "ALERT", "DEFECT", "TRUE") else "OK"
