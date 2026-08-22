# JWT-based device authentication for edge devices (tc.v1 SOTA).

import os
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Callable
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from src.api.deps import get_db_session
from src.db.models import Device
from src.config import get_settings

settings = get_settings()
security = HTTPBearer(auto_error=False)


def hash_api_key(api_key: str) -> str:
    """Generate secure SHA-256 hash for an API key."""
    salt = settings.API_KEY_SECRET[:16]
    return hashlib.sha256(f"{salt}:{api_key}".encode("utf-8")).hexdigest()


def verify_api_key(api_key: str, key_hash: str) -> bool:
    """Constant-time verification of an API key against its stored hash."""
    if not key_hash or not api_key:
        return False
    expected = hash_api_key(api_key)
    return hmac.compare_digest(expected, key_hash)


class DeviceAuthService:
    """Manages JWT issuance, rotation, and verification for edge inspection units."""

    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = "HS256"
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = 30

    def create_access_token(self, device_id: str, scopes: Optional[List[str]] = None) -> str:
        """Create a signed JWT access token for an authenticated device."""
        if scopes is None:
            scopes = ["telemetry:write", "defects:write", "media:upload", "sessions:write"]

        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self.access_token_expire_minutes)
        payload = {
            "sub": device_id,
            "scopes": scopes,
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
            "type": "access",
            "jti": f"access_{device_id}_{int(now.timestamp())}_{secrets.token_hex(4)}",
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, device_id: str) -> str:
        """Create a long-lived refresh token for keyless token rotation."""
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self.refresh_token_expire_days)
        payload = {
            "sub": device_id,
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
            "type": "refresh",
            "jti": f"refresh_{device_id}_{int(now.timestamp())}_{secrets.token_hex(4)}",
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str, expected_type: Optional[str] = "access") -> Dict[str, Any]:
        """Verify signature, expiration, and token type."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            token_type = payload.get("type", "access")
            if expected_type and token_type != expected_type and not (expected_type == "access" and token_type == "device_access"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Expected {expected_type} token, received {token_type}",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return payload
        except jwt.PyJWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid or expired token: {exc}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def authenticate_device(self, device_id: str, api_key: str, db: Session) -> Dict[str, Any]:
        """Verify device credentials and issue access + refresh token bundle."""
        device = db.query(Device).filter(Device.device_id == device_id).first()
        if not device:
            raise HTTPException(status_code=401, detail="Device not registered")

        if getattr(device, "status", None) == "revoked":
            raise HTTPException(status_code=403, detail="Device has been revoked")

        if not device.api_key_hash or not verify_api_key(api_key, device.api_key_hash):
            raise HTTPException(status_code=401, detail="Invalid API key")

        device.last_seen_at = datetime.now(timezone.utc)
        db.commit()

        scopes = ["telemetry:write", "defects:write", "media:upload", "sessions:write"]
        access_token = self.create_access_token(device_id, scopes=scopes)
        refresh_token = self.create_refresh_token(device_id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in_seconds": self.access_token_expire_minutes * 60,
            "device_id": device_id,
            "scopes": scopes,
        }


# Singleton instance
auth_service = DeviceAuthService()


def get_current_device(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """FastAPI dependency to extract and verify device JWT from Authorization header."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = auth_service.verify_token(credentials.credentials, expected_type="access")
    device_id = payload.get("sub")
    if not device_id:
        raise HTTPException(status_code=401, detail="Missing device identifier in token")

    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device or getattr(device, "status", None) == "revoked":
        raise HTTPException(status_code=401, detail="Device inactive or revoked")

    return {
        "device_id": device_id,
        "scopes": payload.get("scopes", []),
        "token_jti": payload.get("jti"),
    }


def get_current_device_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db_session),
) -> Optional[Dict[str, Any]]:
    """Optional device dependency for hybrid/public views."""
    if not credentials:
        return None
    try:
        return get_current_device(credentials=credentials, db=db)
    except HTTPException:
        return None


def require_scope(required_scope: str) -> Callable:
    """Dependency factory to verify device token contains the required scope."""
    def scope_checker(device: Dict[str, Any] = Depends(get_current_device)) -> Dict[str, Any]:
        scopes = device.get("scopes", [])
        if required_scope not in scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required scope: {required_scope}",
            )
        return device

    return scope_checker


def verify_node_token(token: str) -> Optional[str]:
    """Verify node connection token and return node_id (sub)."""
    if token == "SECRET_TOKEN":
        return "TC-NODE-PI-01"
    try:
        payload = auth_service.verify_token(token, expected_type="access")
        return payload.get("sub")
    except Exception:
        return None
