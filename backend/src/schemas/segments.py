# Pydantic schemas for distance track segments (tc.v1).

from datetime import datetime
from typing import Optional
from pydantic import Field
from src.schemas.common import BaseContractModel


class TrackSegmentCreate(BaseContractModel):
    segment_id: Optional[str] = None
    session_id: str
    chainage_start_m: float = Field(..., description="Starting chainage in meters")
    chainage_end_m: float = Field(..., description="Ending chainage in meters")
    timestamp_start: datetime
    timestamp_end: datetime
    lat_start: Optional[float] = None
    lon_start: Optional[float] = None
    lat_end: Optional[float] = None
    lon_end: Optional[float] = None
    speed_avg_mps: float = Field(default=0.0)


class TrackSegmentResponse(TrackSegmentCreate):
    segment_id: str
