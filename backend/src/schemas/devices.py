# Pydantic schemas for edge Raspberry Pi devices (tc.v1).

from datetime import datetime
from typing import Optional
from pydantic import Field
from src.schemas.common import BaseContractModel


class DeviceBase(BaseContractModel):
    device_id: str = Field(..., description="Unique physical device identifier (e.g. RPI-ITMS-001)")
    device_name: str = Field(..., description="Human-readable device name")
    hardware_version: str = Field(..., description="Hardware board/revision version")
    firmware_version: str = Field(..., description="Edge runtime firmware version")
    camera_model: Optional[str] = None
    imu_model: Optional[str] = None
    gnss_model: Optional[str] = None


class DeviceCreate(DeviceBase):
    pass


class DeviceHeartbeat(BaseContractModel):
    battery_voltage_v: Optional[float] = None
    cpu_temp_c: Optional[float] = None
    status: str = Field(default="online", description="Device status: online, recording, error, offline")
    last_seen_at: datetime = Field(default_factory=datetime.utcnow)


class DeviceResponse(DeviceBase):
    status: str
    battery_voltage_v: Optional[float] = None
    cpu_temp_c: Optional[float] = None
    last_seen_at: Optional[datetime] = None
    created_at: datetime
