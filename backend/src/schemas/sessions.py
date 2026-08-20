# Pydantic schemas for monitoring sessions (tc.v1).

from datetime import datetime
from typing import Optional
from pydantic import Field
from src.schemas.common import BaseContractModel


class SessionStartRequest(BaseContractModel):
    device_id: Optional[str] = None
    name: str = Field(..., description="Run mission name")
    route_name: Optional[str] = None
    line_name: Optional[str] = None
    track_id: str
    track_section: str
    track_direction: str = Field(default="both", description="up, down, both")
    start_chainage_m: float = Field(default=0.0)
    operator_name: Optional[str] = None
    weather: Optional[str] = None


class SessionFinishRequest(BaseContractModel):
    end_chainage_m: float
    status: str = Field(default="completed", description="completed, failed")
    defects_count: Optional[int] = None


class SessionResponse(BaseContractModel):
    id: str
    device_id: Optional[str] = None
    name: str
    route_name: Optional[str] = None
    line_name: Optional[str] = None
    track_id: str
    track_section: str
    track_direction: str
    start_time: datetime
    end_time: Optional[datetime] = None
    start_chainage_m: float
    end_chainage_m: float
    status: str
    total_distance_km: float
    defects_count: int
    operator_name: Optional[str] = None
    weather: Optional[str] = None
    created_at: datetime
