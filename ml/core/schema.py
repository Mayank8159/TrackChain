# Shared contracts: ChainageWindow, TrackSegment, GeometryFeatures, CalibratedSignal, SegmentDecision (tc.v1).

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple, Union
from enum import Enum
import numpy as np

SCHEMA_VERSION = "tc.v1"


class DecisionType(str, Enum):
    OK = "OK"
    INSPECT_KNOWN = "INSPECT_KNOWN"
    INSPECT_NOVEL = "INSPECT_NOVEL"


Decision = DecisionType


class SeverityLevel(str, Enum):
    NORMAL = "normal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


Severity = SeverityLevel


class DefectFamily(str, Enum):
    VISUAL_COMPONENT = "visual_component"
    VISUAL_SURFACE = "visual_surface"
    GEOMETRY = "geometry"
    NOVEL_ANOMALY = "novel_anomaly"
    OBSTRUCTION = "obstruction"


class DefectClass(str, Enum):
    NORMAL = "normal"
    MISSING_FASTENER = "missing_fastener"
    DAMAGED_FASTENER = "damaged_fastener"
    CRACK = "crack"
    CORRUGATION = "corrugation"
    SPALLING = "spalling"
    SQUAT = "squat"
    GAUGE_WIDENING = "gauge_widening"
    ALIGNMENT_FAULT = "alignment_fault"
    TWIST_EXCEEDANCE = "twist_exceedance"
    ROUGH_TRACK = "rough_track"
    DIPPED_JOINT = "dipped_joint"
    CYCLIC_TOP = "cyclic_top"
    TWIST_FAULT = "twist_fault"
    ALIGNMENT_KINK = "alignment_kink"
    BUCKLING_RISK = "buckling_risk"
    OBSTRUCTION = "obstruction"
    VISUAL_ANOMALY = "visual_anomaly"
    GEOMETRY_ANOMALY = "geometry_anomaly"
    UNCLASSIFIED = "unclassified_anomaly"


class SignalType(str, Enum):
    VISUAL_KNOWN = "visual_known"
    VISUAL_NOVEL = "visual_novel"
    GEOMETRY_KNOWN = "geometry_known"
    GEOMETRY_NOVEL = "geometry_novel"
    GEOMETRY_FAULT_TYPE = "geometry_known_type"
    GEOMETRY_KNOWN_TYPE = "geometry_known_type"


@dataclass
class ChainageWindow:
    """Represents a discrete physical distance window along the railway track."""
    start_chainage_m: float
    end_chainage_m: float
    timestamps: np.ndarray
    distances: np.ndarray
    raw_telemetry: Dict[str, np.ndarray] = field(default_factory=dict)
    frames: List[np.ndarray] = field(default_factory=list)


@dataclass
class TrackSegment:
    """Unified physical track segment bundling spatial coordinates, vision frames, and telemetry."""
    segment_id: str
    chainage_start_m: float
    chainage_end_m: float
    timestamp: Optional[Any] = None
    frames: List[np.ndarray] = field(default_factory=list)
    telemetry: Dict[str, np.ndarray] = field(default_factory=dict)
    section_type: str = "mainline_standard"


@dataclass
class ExplainabilityTrace:
    """Detailed explainability trace linking an ML decision back to raw model signals and spatial bins."""
    model_name: str
    signal_type: SignalType
    raw_score: float
    calibrated_score: float
    threshold: float
    fired: bool
    spatial_bin: int = 0
    attention_peak: Optional[int] = None
    reconstruction_error: Optional[float] = None


@dataclass
class GeometryFeatures:
    """Deterministic track geometry metrics compliant with EN 13848-1."""
    chainage_m: float
    gauge_dev_mm: float
    cant_mm: float
    twist_3m_mm_per_m: float
    vertical_profile_d1_mm: float
    alignment_d1_mm: float
    rms_vibration_g: float


@dataclass
class CalibratedSignal:
    """Output of a model after temperature scaling or threshold calibration."""
    stream_name: str = "signal"
    raw_score: float = 0.0
    calibrated_prob: float = 0.0
    predicted_class: Optional[DefectClass] = None
    is_anomaly: bool = False
    signal_type: SignalType = SignalType.VISUAL_KNOWN
    threshold: float = 0.5
    bbox: Optional[Tuple[float, float, float, float]] = None  # (x1, y1, x2, y2)
    explanation: Optional[Union[str, Dict[str, Any]]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __init__(
        self,
        stream_name: Optional[str] = None,
        raw_score: float = 0.0,
        calibrated_prob: Optional[float] = None,
        predicted_class: Optional[DefectClass] = None,
        is_anomaly: Optional[bool] = None,
        signal_type: SignalType = SignalType.VISUAL_KNOWN,
        threshold: float = 0.5,
        bbox: Optional[Tuple[float, float, float, float]] = None,
        explanation: Optional[Union[str, Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
        value: Optional[float] = None,
        label: Optional[DefectClass] = None,
        fired: Optional[bool] = None,
        model_version: Optional[str] = None,
        **kwargs,
    ):
        self.stream_name = stream_name or name or "signal"
        self.raw_score = float(raw_score)
        self.calibrated_prob = float(calibrated_prob if calibrated_prob is not None else (value if value is not None else 0.0))
        self.predicted_class = predicted_class if predicted_class is not None else label
        self.is_anomaly = is_anomaly if is_anomaly is not None else (fired if fired is not None else False)
        self.signal_type = signal_type
        self.threshold = float(threshold)
        self.bbox = bbox
        self.explanation = explanation
        self.metadata = metadata or {}
        if model_version:
            self.metadata["model_version"] = model_version
        if kwargs:
            self.metadata.update(kwargs)

    @property
    def name(self) -> str:
        return self.stream_name

    @property
    def value(self) -> float:
        return self.calibrated_prob

    @property
    def fired(self) -> bool:
        return self.is_anomaly

    @property
    def label(self) -> Optional[DefectClass]:
        return self.predicted_class

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.stream_name,
            "stream_name": self.stream_name,
            "model_version": self.metadata.get("model_version", "0.1.0"),
            "signal_type": self.signal_type.value if hasattr(self.signal_type, "value") else str(self.signal_type),
            "value": float(self.calibrated_prob),
            "raw_score": float(self.raw_score),
            "calibrated_prob": float(self.calibrated_prob),
            "threshold": float(self.threshold),
            "fired": bool(self.is_anomaly),
            "is_anomaly": bool(self.is_anomaly),
            "predicted_class": self.predicted_class.value if hasattr(self.predicted_class, "value") else str(self.predicted_class) if self.predicted_class else None,
            "bbox": list(self.bbox) if self.bbox else None,
            "explanation": self.explanation,
            "metadata": self.metadata,
        }


@dataclass
class SegmentSignals:
    """Unified collection of multi-modal signals associated with a TrackSegment."""
    v_known: List[CalibratedSignal] = field(default_factory=list)
    v_novel: List[CalibratedSignal] = field(default_factory=list)
    g_known: List[CalibratedSignal] = field(default_factory=list)
    g_novel: List[CalibratedSignal] = field(default_factory=list)
    g_type: List[CalibratedSignal] = field(default_factory=list)

    @property
    def all_signals(self) -> List[CalibratedSignal]:
        return self.v_known + self.v_novel + self.g_known + self.g_novel + self.g_type

    def get_primary(self, signal_type: SignalType) -> CalibratedSignal:
        """Extract the most prominent CalibratedSignal matching the given stream type."""
        matching = [s for s in self.all_signals if s.signal_type == signal_type]
        if matching:
            # Return signal with highest calibrated probability or fired status
            return max(matching, key=lambda s: (s.is_anomaly, s.calibrated_prob))
        return CalibratedSignal(
            stream_name=signal_type.value,
            raw_score=0.0,
            calibrated_prob=0.0,
            signal_type=signal_type,
            is_anomaly=False,
            predicted_class=DefectClass.NORMAL,
        )


@dataclass
class MediaReference:
    """Metadata pointing to S3 media asset associated with an ML inference result."""
    media_id: Optional[str] = None
    s3_key: Optional[str] = None
    offset_seconds: float = 0.0
    frame_index: Optional[int] = None


@dataclass
class SegmentDecision:
    """Final operational decision emitted by the persistence rule fusion engine for a track segment."""
    window_id: str = "win-00000"
    start_chainage_m: float = 0.0
    end_chainage_m: float = 0.0
    decision: DecisionType = DecisionType.OK
    confidence: float = 0.98
    primary_fault: Optional[Union[DefectClass, str]] = None
    defect_family: DefectFamily = DefectFamily.VISUAL_COMPONENT
    severity: SeverityLevel = SeverityLevel.LOW
    signals: List[CalibratedSignal] = field(default_factory=list)
    evidence: Optional[MediaReference] = None
    timestamp: Optional[str] = None
    schema_version: str = SCHEMA_VERSION
    source: Optional[str] = None
    cross_modal_boost: float = 1.0
    traces: List[ExplainabilityTrace] = field(default_factory=list)

    def __init__(
        self,
        decision: Optional[DecisionType] = None,
        primary_fault: Optional[Union[DefectClass, str]] = None,
        severity: Optional[SeverityLevel] = None,
        window_id: str = "win-00000",
        start_chainage_m: float = 0.0,
        end_chainage_m: float = 0.0,
        confidence: float = 0.98,
        defect_family: DefectFamily = DefectFamily.VISUAL_COMPONENT,
        signals: Optional[List[CalibratedSignal]] = None,
        evidence: Optional[MediaReference] = None,
        timestamp: Optional[str] = None,
        schema_version: str = SCHEMA_VERSION,
        source: Optional[str] = None,
        cross_modal_boost: float = 1.0,
        traces: Optional[List[ExplainabilityTrace]] = None,
        **kwargs,
    ):
        self.decision = decision if decision is not None else DecisionType.OK
        self.primary_fault = primary_fault or kwargs.get("primary_defect")
        self.severity = severity if severity is not None else SeverityLevel.LOW
        self.window_id = window_id
        self.start_chainage_m = float(start_chainage_m if start_chainage_m != 0.0 else kwargs.get("chainage_start_m", 0.0))
        self.end_chainage_m = float(end_chainage_m if end_chainage_m != 0.0 else kwargs.get("chainage_end_m", 0.0))
        self.confidence = float(confidence)
        self.defect_family = defect_family
        self.signals = signals if signals is not None else []
        self.evidence = evidence
        self.timestamp = timestamp
        self.schema_version = schema_version
        self.source = source
        self.cross_modal_boost = float(cross_modal_boost)
        self.traces = traces if traces is not None else []
        for k, v in kwargs.items():
            if k in ("chainage_start_m", "start_chainage_m"):
                self.start_chainage_m = float(v)
            elif k in ("chainage_end_m", "end_chainage_m"):
                self.end_chainage_m = float(v)
            elif k in ("primary_defect", "primary_fault"):
                self.primary_fault = v
            else:
                setattr(self, k, v)

    @property
    def primary_defect(self) -> Optional[Union[DefectClass, str]]:
        return self.primary_fault

    @primary_defect.setter
    def primary_defect(self, value: Optional[Union[DefectClass, str]]) -> None:
        self.primary_fault = value

    @property
    def chainage_start_m(self) -> float:
        return self.start_chainage_m

    @chainage_start_m.setter
    def chainage_start_m(self, value: float) -> None:
        self.start_chainage_m = float(value)

    @property
    def chainage_end_m(self) -> float:
        return self.end_chainage_m

    @chainage_end_m.setter
    def chainage_end_m(self, value: float) -> None:
        self.end_chainage_m = float(value)

    def to_dict(self) -> Dict[str, Any]:
        prim_def = self.primary_fault
        if hasattr(prim_def, "value"):
            prim_def_str = prim_def.value
        elif prim_def is not None:
            prim_def_str = str(prim_def)
        else:
            prim_def_str = None

        return {
            "schema_version": self.schema_version,
            "window_id": self.window_id,
            "chainage_start_m": float(self.start_chainage_m),
            "chainage_end_m": float(self.end_chainage_m),
            "start_chainage_m": float(self.start_chainage_m),
            "end_chainage_m": float(self.end_chainage_m),
            "decision": self.decision.value if hasattr(self.decision, "value") else str(self.decision),
            "severity": self.severity.value if hasattr(self.severity, "value") else str(self.severity),
            "confidence": round(float(self.confidence), 4),
            "primary_defect": prim_def_str,
            "primary_fault": prim_def_str,
            "action": getattr(self, "action", "Routine inspection cycle maintained."),
            "section_type": getattr(self, "section_type", "mainline_standard"),
            "cross_modal_boost": float(self.cross_modal_boost),
            "signals": [s.to_dict() if hasattr(s, "to_dict") else s for s in self.signals],
            "timestamp": self.timestamp,
        }
