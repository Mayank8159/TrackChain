# Edge inspection devices registration and heartbeat management (tc.v1).

from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.api.deps import get_db_session
from src.db.models import Device
from src.schemas.devices import DeviceCreate, DeviceHeartbeat, DeviceResponse

router = APIRouter(prefix="/api/devices", tags=["Devices"])


@router.post("", response_model=DeviceResponse)
def register_device(payload: DeviceCreate, db: Session = Depends(get_db_session)):
    """Register or update an edge inspection unit."""
    device = db.query(Device).filter(Device.device_id == payload.device_id).first()
    if not device:
        device = Device(
            device_id=payload.device_id,
            device_name=payload.device_name,
            hardware_version=payload.hardware_version,
            firmware_version=payload.firmware_version,
            camera_model=payload.camera_model,
            imu_model=payload.imu_model,
            gnss_model=payload.gnss_model,
            status="online",
            last_seen_at=datetime.utcnow(),
        )
        db.add(device)
    else:
        device.device_name = payload.device_name
        device.hardware_version = payload.hardware_version
        device.firmware_version = payload.firmware_version
        device.camera_model = payload.camera_model
        device.imu_model = payload.imu_model
        device.gnss_model = payload.gnss_model
        device.last_seen_at = datetime.utcnow()

    db.commit()
    db.refresh(device)
    return device


@router.post("/{device_id}/heartbeat", response_model=DeviceResponse)
def device_heartbeat(
    device_id: str,
    payload: DeviceHeartbeat,
    db: Session = Depends(get_db_session),
):
    """Receive periodic telemetry heartbeat from edge Raspberry Pi."""
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not registered")

    device.battery_voltage_v = payload.battery_voltage_v
    device.cpu_temp_c = payload.cpu_temp_c
    device.status = payload.status
    device.last_seen_at = payload.last_seen_at
    db.commit()
    db.refresh(device)
    return device


@router.get("", response_model=List[DeviceResponse])
def list_devices(db: Session = Depends(get_db_session)):
    """List all registered edge inspection units."""
    return db.query(Device).order_by(Device.created_at.desc()).all()
