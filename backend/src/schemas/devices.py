# Pydantic schemas for edge Raspberry Pi devices (tc.v1).

from datetime import datetime, timezone
from typing import Optional, List
from pydantic import Field
from src.schemas.common import BaseContractModel


class DeviceBase(BaseContractModel):
    device_id: str = Field(..., description="Unique physical device identifier (e.g. RPI-ITMS-001)")
    device_name: str = Field(default="Edge Device", description="Human-readable device name")
    hardware_version: str = Field(default="Raspberry Pi 5", description="Hardware board/revision version")
    firmware_version: str = Field(default="v1.0.0", description="Edge runtime firmware version")
    camera_model: Optional[str] = None
    imu_model: Optional[str] = None
    gnss_model: Optional[str] = None


class DeviceCreate(DeviceBase):
    pass


class DeviceRegisterRequest(BaseContractModel):
    device_id: str
    device_name: Optional[str] = None
    name: Optional[str] = None
    hardware_version: Optional[str] = "Raspberry Pi 5"
    firmware_version: Optional[str] = "v1.0.0"
    camera_model: Optional[str] = None
    imu_model: Optional[str] = None
    gnss_model: Optional[str] = None

    def get_name(self) -> str:
        return self.device_name or self.name or f"Edge Node {self.device_id}"


class DeviceRegisterResponse(BaseContractModel):
    device_id: str
    api_key: str
    message: str = "Store this API key securely. It cannot be retrieved again."
    status: str = "registered"


class DeviceTokenRequest(BaseContractModel):
    device_id: str
    api_key: str


class RefreshTokenRequest(BaseContractModel):
    refresh_token: str


class DeviceTokenResponse(BaseContractModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in_seconds: int = 3600
    device_id: Optional[str] = None
    scopes: List[str] = ["telemetry:write", "defects:write", "media:upload", "sessions:write"]


class DeviceHeartbeat(BaseContractModel):
    battery_voltage_v: Optional[float] = None
    cpu_temp_c: Optional[float] = None
    status: str = Field(default="online", description="Device status: online, recording, error, offline")
    last_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DeviceResponse(DeviceBase):
    status: str
    battery_voltage_v: Optional[float] = None
    cpu_temp_c: Optional[float] = None
    last_seen_at: Optional[datetime] = None
    created_at: datetime
