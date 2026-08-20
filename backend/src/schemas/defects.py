# Pydantic schemas for defect events, explainability signals, and operational incident management (tc.v1 SOTA).

from datetime import datetime
from typing import Optional, List
from pydantic import Field
from src.schemas.common import BaseContractModel
from src.schemas.ml import MLSignalCreate, MLSignalResponse


class DefectEventBase(BaseContractModel):
    chainage_m: float = Field(..., description="Location of defect along track in meters")
    chainage_start_m: Optional[float] = None
    chainage_end_m: Optional[float] = None
    defect_class: str = Field(..., description="missing_fastener, crack, spalling, gauge_widening, etc.")
    defect_family: str = Field(default="visual_component", description="visual_component, visual_surface, geometry, novel_anomaly, obstruction")
    severity: str = Field(..., description="low, medium, high, critical")
    decision: str = Field(default="INSPECT_KNOWN", description="OK, INSPECT_KNOWN, INSPECT_NOVEL")
    confidence: float = Field(..., ge=0.0, le=1.0)
    source_model: str = Field(default="yolo_v8_detector", description="Detector or fusion model name")
    model_version: Optional[str] = None
    stream_source: str = Field(default="fused", description="vision, geometry, fused")

    latitude: Optional[float] = None
    longitude: Optional[float] = None

    image_url: Optional[str] = None
    evidence_image_id: Optional[str] = None
    video_media_id: Optional[str] = None
    video_timestamp_sec: Optional[float] = None
    video_offset_seconds: Optional[float] = None

    description: Optional[str] = None
    status: str = Field(default="open", description="open, acknowledged, assigned, resolved, false_positive")
    notes: Optional[str] = None


class DefectEventCreate(DefectEventBase):
    session_id: str
    device_id: Optional[str] = None
    segment_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    supporting_signals: Optional[List[MLSignalCreate]] = Field(default_factory=list)


class DefectEventUpdate(BaseContractModel):
    status: Optional[str] = None
    severity: Optional[str] = None
    notes: Optional[str] = None
    acknowledged_by: Optional[str] = None


class DefectEventResponse(DefectEventBase):
    id: str
    session_id: str
    device_id: Optional[str] = None
    segment_id: Optional[str] = None
    timestamp: datetime
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    supporting_signals: Optional[List[MLSignalResponse]] = None


# Backward-compatibility aliases
DefectCreate = DefectEventCreate
DefectResponse = DefectEventResponse


class DefectFilterParams(BaseContractModel):
    session_id: Optional[str] = None
    defect_class: Optional[str] = None
    defect_family: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    chainage_min: Optional[float] = None
    chainage_max: Optional[float] = None
    source_model: Optional[str] = None


class DefectSummaryResponse(BaseContractModel):
    total_defects: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    open_count: int
