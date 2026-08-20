# Shared contracts: ChainageWindow, GeometryFeatures, CalibratedSignal, SegmentDecision.

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import numpy as np


class DecisionType(str, Enum):
    OK = "OK"
    KNOWN = "KNOWN"
    NOVEL = "NOVEL"


class DefectClass(str, Enum):
    CRACK = "crack"
    SPALLING = "spalling"
    CORRUGATION = "corrugation"
    MISSING_FASTENER = "missing_fastener"
    GAUGE_WIDENING = "gauge_widening"
    ALIGNMENT_FAULT = "alignment_fault"
    TWIST_EXCEEDANCE = "twist_exceedance"
    SQUAT = "squat"
    UNCLASSIFIED = "unclassified_anomaly"


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
    stream_name: str  # "vision_detector", "vision_anomaly", "geometry_lstm", "geometry_vae"
    raw_score: float
    calibrated_prob: float
    predicted_class: Optional[DefectClass] = None
    is_anomaly: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SegmentDecision:
    """Final decision emitted by the persistence rule fusion engine for a track window."""
    window_id: str
    start_chainage_m: float
    end_chainage_m: float
    decision: DecisionType
    confidence: float
    primary_fault: Optional[DefectClass] = None
    signals: List[CalibratedSignal] = field(default_factory=list)
    timestamp: Optional[str] = None
