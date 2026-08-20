# Pydantic models for defect events and query filters.

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DefectCreate(BaseModel):
    session_id: str
    timestamp: Optional[datetime] = None
    chainage_m: float
    defect_class: str
    severity: str = "medium"  # normal, low, medium, high, critical
    confidence: float = Field(ge=0.0, le=1.0)
    stream_source: str = "vision"  # vision, geometry, fused
    image_url: Optional[str] = None
    video_timestamp_sec: Optional[float] = None
    description: Optional[str] = None
    status: str = "open"
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class DefectResponse(DefectCreate):
    id: str

    class Config:
        from_attributes = True


class DefectFilterParams(BaseModel):
    session_id: Optional[str] = None
    severity: Optional[str] = None
    defect_class: Optional[str] = None
    stream_source: Optional[str] = None
    min_chainage: Optional[float] = None
    max_chainage: Optional[float] = None
