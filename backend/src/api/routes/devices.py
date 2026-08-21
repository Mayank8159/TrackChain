# Edge inspection devices registration and heartbeat management (tc.v1 SOTA).

import secrets
from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.api.deps import get_db_session
from src.db.models import Device
from src.schemas.devices import (
    DeviceCreate,
    DeviceHeartbeat,
    DeviceResponse,
    DeviceRegisterRequest,
    DeviceRegisterResponse,
    DeviceTokenRequest,
    DeviceTokenResponse,
    RefreshTokenRequest,
)
from src.services.auth import auth_service, hash_api_key
from src.services.audit import AuditService

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.post("/register", response_model=DeviceRegisterResponse)
def register_new_device(payload: DeviceRegisterRequest, db: Session = Depends(get_db_session)):
    """Register a new edge device and issue a cryptographically secure API key."""
    raw_api_key = f"tc_live_{secrets.token_urlsafe(32)}"
    api_hash = hash_api_key(raw_api_key)
    name = payload.get_name()

    device = db.query(Device).filter(Device.device_id == payload.device_id).first()
    if not device:
        device = Device(
            device_id=payload.device_id,
            device_name=name,
            hardware_version=payload.hardware_version or "Raspberry Pi 5",
            firmware_version=payload.firmware_version or "v1.0.0",
            camera_model=payload.camera_model,
            imu_model=payload.imu_model,
            gnss_model=payload.gnss_model,
            status="active",
            api_key_hash=api_hash,
            last_seen_at=datetime.now(timezone.utc),
        )
        db.add(device)
    else:
        device.device_name = name
        device.api_key_hash = api_hash
        device.status = "active"
        device.last_seen_at = datetime.now(timezone.utc)

    db.commit()

    # Record immutable audit event
    AuditService.log_sync(
        actor_type="system",
        actor_id="registration_authority",
        action="device.registered",
        resource_type="device",
        resource_id=payload.device_id,
        details={"device_name": name, "hardware_version": payload.hardware_version},
        db=db,
    )

    return DeviceRegisterResponse(
        device_id=payload.device_id,
        api_key=raw_api_key,
        message="Store this API key securely. It cannot be retrieved again.",
        status="registered",
    )


@router.post("/token", response_model=DeviceTokenResponse)
def exchange_api_key_for_token(payload: DeviceTokenRequest, db: Session = Depends(get_db_session)):
    """Exchange a valid device API key for a short-lived JWT access token and refresh token."""
    token_bundle = auth_service.authenticate_device(
        device_id=payload.device_id,
        api_key=payload.api_key,
        db=db,
    )
    return DeviceTokenResponse(
        access_token=token_bundle["access_token"],
        refresh_token=token_bundle["refresh_token"],
        token_type="bearer",
        expires_in_seconds=token_bundle["expires_in_seconds"],
        device_id=payload.device_id,
        scopes=token_bundle["scopes"],
    )


@router.post("/refresh", response_model=DeviceTokenResponse)
def refresh_device_token(payload: RefreshTokenRequest, db: Session = Depends(get_db_session)):
    """Rotate JWT access token using a valid refresh token."""
    decoded = auth_service.verify_token(payload.refresh_token, expected_type="refresh")
    device_id = decoded.get("sub")
    if not device_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device or getattr(device, "status", None) == "revoked":
        raise HTTPException(status_code=401, detail="Device inactive or revoked")

    scopes = ["telemetry:write", "defects:write", "media:upload", "sessions:write"]
    new_access_token = auth_service.create_access_token(device_id, scopes=scopes)
    new_refresh_token = auth_service.create_refresh_token(device_id)

    return DeviceTokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in_seconds=3600,
        device_id=device_id,
        scopes=scopes,
    )


@router.post("/revoke")
def revoke_device(device_id: str, db: Session = Depends(get_db_session)):
    """Revoke a compromised edge device (blocks future token exchange)."""
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    device.status = "revoked"
    db.commit()

    AuditService.log_sync(
        actor_type="system",
        actor_id="security_admin",
        action="device.revoked",
        resource_type="device",
        resource_id=device_id,
        details={"status": "revoked"},
        db=db,
    )

    return {"status": "revoked", "device_id": device_id}


@router.post("", response_model=DeviceResponse)
def register_device(payload: DeviceCreate, db: Session = Depends(get_db_session)):
    """Register or update an edge inspection unit."""
    device = db.query(Device).filter(Device.device_id == payload.device_id).first()
    now = datetime.now(timezone.utc)
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
            last_seen_at=now,
        )
        db.add(device)
    else:
        device.device_name = payload.device_name
        device.hardware_version = payload.hardware_version
        device.firmware_version = payload.firmware_version
        device.camera_model = payload.camera_model
        device.imu_model = payload.imu_model
        device.gnss_model = payload.gnss_model
        device.last_seen_at = now

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
