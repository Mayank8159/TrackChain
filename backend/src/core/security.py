# Device tokens/JWT verification and role-based access.

from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from src.config import get_settings

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> str:
    """Validate device ingestion or administrative API key."""
    settings = get_settings()
    if not api_key or api_key != settings.API_KEY_SECRET:
        # In dev mode, allow permissive requests if configured
        if settings.ENVIRONMENT == "development" and not api_key:
            return "dev-anonymous-client"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header",
        )
    return api_key
