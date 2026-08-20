# Shared contracts: ChainageWindow, GeometryFeatures, CalibratedSignal, SegmentDecision (tc.v1).

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
import numpy as np

SCHEMA_VERSION = "tc.v1"


class DecisionType(str, Enum):
    OK = "OK"
    INSPECT_KNOWN = "INSPECT_KNOWN"
    INSPECT_NOVEL = "INSPECT_NOVEL"


class SeverityLevel(str, Enum):
    NORMAL = "normal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DefectFamily(str, Enum):
    VISUAL_COMPONENT = "visual_component"
    VISUAL_SURFACE = "visual_surface"
    GEOMETRY = "geometry"
    NOVEL_ANOMALY = "novel_anomaly"
    OBSTRUCTION = "obstruction"


class DefectClass(str, Enum):
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
    OBSTRUCTION = "obstruction"
    VISUAL_ANOMALY = "visual_anomaly"
    GEOMETRY_ANOMALY = "geometry_anomaly"
    UNCLASSIFIED = "unclassified_anomaly"


class SignalType(str, Enum):
    VISUAL_KNOWN = "visual_known"
    VISUAL_NOVEL = "visual_novel"
    GEOMETRY_KNOWN = "geometry_known"
    GEOMETRY_NOVEL = "geometry_novel"
    GEOMETRY_FAULT_TYPE = "geometry_fault_type"


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
    stream_name: str  # e.g. "vision_detector", "vision_anomaly", "geometry_lstm", "geometry_vae"
    raw_score: float
    calibrated_prob: float
    predicted_class: Optional[DefectClass] = None
    is_anomaly: bool = False
    signal_type: SignalType = SignalType.VISUAL_KNOWN
    threshold: float = 0.5
    bbox: Optional[Tuple[float, float, float, float]] = None  # (x1, y1, x2, y2)
    explanation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


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
    window_id: str
    start_chainage_m: float
    end_chainage_m: float
    decision: DecisionType
    confidence: float
    primary_fault: Optional[DefectClass] = None
    defect_family: DefectFamily = DefectFamily.VISUAL_COMPONENT
    severity: SeverityLevel = SeverityLevel.LOW
    signals: List[CalibratedSignal] = field(default_factory=list)
    evidence: Optional[MediaReference] = None
    timestamp: Optional[str] = None
    schema_version: str = SCHEMA_VERSION
