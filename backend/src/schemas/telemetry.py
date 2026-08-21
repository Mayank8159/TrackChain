from datetime import datetime, timezone
from typing import List, Optional, Tuple, Any, Union
from pydantic import Field, field_validator
from src.schemas.common import BaseContractModel, IdempotentRequest


class TelemetrySampleBase(BaseContractModel):
    chainage_m: float = Field(..., description="Distance along track in meters")
    timestamp: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    segment_id: Optional[str] = None

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, v: Any) -> datetime:
        if v is None:
            return datetime.now(timezone.utc)
        if isinstance(v, (int, float)):
            # If timestamp is in milliseconds (e.g. > 1e11)
            if v > 1e11:
                v = v / 1000.0
            return datetime.fromtimestamp(v, tz=timezone.utc)
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00"))
            except Exception:
                pass
        return v

    # Spatial & Kinematics
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude_m: Optional[float] = None
    gnss_fix_quality: Optional[int] = None
    gnss_satellites: Optional[int] = None
    speed_mps: float = Field(default=0.0)
    speed_kmh: Optional[float] = None

    # IMU Data
    imu_ax: Optional[float] = None
    imu_ay: Optional[float] = None
    imu_az: Optional[float] = None
    imu_gx: Optional[float] = None
    imu_gy: Optional[float] = None
    imu_gz: Optional[float] = None
    roll_deg: Optional[float] = None
    pitch_deg: Optional[float] = None
    yaw_deg: Optional[float] = None

    # Dynamics & EN 13848 Track Geometry
    vertical_rms: float = Field(default=0.0)
    lateral_rms: float = Field(default=0.0)
    longitudinal_rms: float = Field(default=0.0)
    vibration_rms: float = Field(default=0.0)
    vibration_index: float = Field(default=0.0)
    track_gauge_mm: float = Field(default=1435.0)
    gauge_mm: Optional[float] = Field(default=None)
    cant_mm: float = Field(default=0.0)
    twist_mm_per_m: float = Field(default=0.0)
    vertical_unevenness_mm: float = Field(default=0.0)
    alignment_dev_mm: float = Field(default=0.0)

    def model_post_init(self, __context):
        if self.gauge_mm is not None:
            self.track_gauge_mm = self.gauge_mm

    # Diagnostics
    temperature_c: Optional[float] = None
    battery_voltage_v: Optional[float] = None


class TelemetrySampleCreate(TelemetrySampleBase):
    session_id: Optional[str] = None


class TelemetrySampleResponse(TelemetrySampleBase):
    id: str
    session_id: str
    device_id: Optional[str] = None


# Aliases for backward compatibility with route handlers
TelemetryPointCreate = TelemetrySampleCreate
TelemetryPointResponse = TelemetrySampleResponse


class TelemetryBatchIngestRequest(IdempotentRequest):
    session_id: str
    device_id: Optional[str] = None
    samples: List[TelemetrySampleCreate] = Field(default_factory=list)
    points: Optional[List[TelemetrySampleCreate]] = Field(default=None)

    def model_post_init(self, __context):
        if self.points and not self.samples:
            self.samples = self.points


TelemetryBatchRequest = TelemetryBatchIngestRequest


class TelemetryQueryResponse(BaseContractModel):
    session_id: str
    count: int
    samples: List[TelemetrySampleResponse]


class LineGeometry(BaseContractModel):
    x1: float
    y1: float
    x2: float
    y2: float
    angle_deg: float
    length: float


class ProcessFrameRequest(BaseContractModel):
    camera_id: str = Field(default="cam-01")
    frame: str = Field(..., description="Base64 encoded JPEG/PNG frame")
    trace_id: Optional[str] = None


class ProcessFrameResponse(BaseContractModel):
    camera_id: str
    resolution: Tuple[int, int]
    line_count: int
    lines: List[LineGeometry]
    rails: List[LineGeometry] = Field(default_factory=list)
    sleepers: List[LineGeometry] = Field(default_factory=list)
    processing_ms: float
    inference_ms: Optional[float] = None
    yolo_weights_loaded: bool = False
    yolo_boxes: List[dict] = Field(default_factory=list)
    status: str
    vision_status: Optional[str] = Field(default="OK")
    vision_confidence_score: Optional[float] = Field(default=1.0)

