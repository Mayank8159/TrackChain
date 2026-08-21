from datetime import datetime, timezone
from typing import List, Optional, Tuple
from pydantic import Field
from src.schemas.common import BaseContractModel, IdempotentRequest


class TelemetrySampleBase(BaseContractModel):
    chainage_m: float = Field(..., description="Distance along track in meters")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    segment_id: Optional[str] = None

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
    cant_mm: float = Field(default=0.0)
    twist_mm_per_m: float = Field(default=0.0)
    vertical_unevenness_mm: float = Field(default=0.0)
    alignment_dev_mm: float = Field(default=0.0)

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


class ProcessFrameResponse(BaseContractModel):
    camera_id: str
    resolution: Tuple[int, int]
    line_count: int
    lines: List[LineGeometry]
    processing_ms: float
    status: str
