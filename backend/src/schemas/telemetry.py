# Pydantic request/response models for telemetry payloads.

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class TelemetryPointCreate(BaseModel):
    session_id: str
    timestamp: Optional[datetime] = None
    chainage_m: float
    speed_kmh: float = 0.0
    vibration_rms: float = 0.0
    track_gauge_mm: float = 1435.0
    cant_mm: float = 0.0
    twist_mm_per_m: float = 0.0
    vertical_unevenness_mm: float = 0.0
    alignment_dev_mm: float = 0.0
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class TelemetryPointResponse(TelemetryPointCreate):
    id: str

    class Config:
        from_attributes = True


class TelemetryBatchRequest(BaseModel):
    points: List[TelemetryPointCreate]


class LineGeometry(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float
    angle_deg: float
    length: float


class ProcessFrameRequest(BaseModel):
    frame: str = Field(..., description="Base64-encoded JPEG / PNG frame")
    camera_id: str = Field(default="cam-00", description="Source camera identifier")


class ProcessFrameResponse(BaseModel):
    camera_id: str
    resolution: List[int] = Field(..., description="[width, height] of processed frame")
    line_count: int
    lines: List[LineGeometry]
    processing_ms: float
    status: str = "ok"
