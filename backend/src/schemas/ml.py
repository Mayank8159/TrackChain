# Pydantic schemas for ML signals, fusion decisions, calibration, and registry (tc.v1 SOTA).

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import Field
from src.schemas.common import BaseContractModel, IdempotentRequest


class MLSignalBase(BaseContractModel):
    model_name: str = Field(..., description="Name of model (e.g. yolo_v8_detector, patchcore_anomaly)")
    model_version: str = Field(..., description="Model version (e.g. 0.1.0)")
    signal_type: str = Field(..., description="visual_known, visual_novel, geometry_known, geometry_novel")
    raw_score: float
    calibrated_score: float
    threshold: float
    fired: bool
    label: Optional[str] = None
    bbox: Optional[List[float]] = None  # [x1, y1, x2, y2]
    explanation: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MLSignalCreate(MLSignalBase):
    session_id: Optional[str] = None
    segment_id: Optional[str] = None
    defect_id: Optional[str] = None


class MLSignalResponse(MLSignalBase):
    signal_id: str
    session_id: str
    segment_id: Optional[str] = None
    defect_id: Optional[str] = None


class MLSignalBatchRequest(IdempotentRequest):
    session_id: str
    segment_id: Optional[str] = None
    signals: List[MLSignalCreate]


class SegmentDecisionPayload(BaseContractModel):
    segment_id: str
    decision: str = Field(..., description="OK, INSPECT_KNOWN, INSPECT_NOVEL")
    confidence: float
    primary_fault: Optional[str] = None
    all_model_signals: List[MLSignalBase] = Field(default_factory=list)
    evidence_reference: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CalibrationArtifactSchema(BaseContractModel):
    calibration_id: str
    model_name: str
    model_version: str
    method: str
    target_fpr: float
    threshold: float
    temperature: Optional[float] = None
    validation_dataset: str
    metrics_summary: Optional[Dict[str, float]] = None
    created_at: datetime


class ModelRegistrySchema(BaseContractModel):
    model_name: str
    model_version: str
    model_type: str
    artifact_uri: str
    input_contract_version: str = Field(default="tc.v1")
    output_contract_version: str = Field(default="tc.v1")
    trained_on: Optional[str] = None
    metrics: Optional[Dict[str, float]] = None
    is_active: bool = True
    created_at: datetime
