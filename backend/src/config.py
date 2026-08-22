# Settings loader (pydantic-settings) reading environment variables.

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Pre-load .env from possible candidate locations
_backend_dir = Path(__file__).resolve().parent.parent
_repo_dir = _backend_dir.parent

for env_candidate in [_backend_dir / ".env", _repo_dir / ".env", Path(".env")]:
    if env_candidate.exists() and env_candidate.is_file():
        load_dotenv(dotenv_path=env_candidate, override=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", str(_backend_dir / ".env"), str(_repo_dir / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General
    PROJECT_NAME: str = "TrackChain Backend API"
    VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False

    # Database (PostgreSQL / TimescaleDB)
    DATABASE_URL: str = "postgresql+psycopg2://trackchain:trackchain_secret@localhost:5432/trackchain_db"

    # Redis (Rate limiting and caching)
    REDIS_URL: Optional[str] = "redis://localhost:6379/0"

    # S3 / MinIO / Local Storage
    STORAGE_BACKEND: str = "local"  # "s3" or "local"
    S3_ENDPOINT_URL: Optional[str] = "http://localhost:9000"
    S3_PUBLIC_ENDPOINT: Optional[str] = None
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "trackchain-media"
    MODEL_BUCKET: str = "trackchain-models-prod"
    S3_REGION: str = "us-east-1"

    # Security & Auth
    API_KEY_SECRET: str = "trackchain-super-secret-key"
    JWT_SECRET_KEY: str = "trackchain-jwt-secret-key-change-in-production"
    REQUEST_SIGNING_SECRET: str = "trackchain-request-signing-secret-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # CORS Allowlist
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://trackchain.vercel.app",
        "https://trackchain-app.vercel.app",
    ]

    # Rate Limiting (per-device token bucket)
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 10

    # Webhooks (RDSO / UDM / TMS Integrations)
    RDSO_WEBHOOK_URL: Optional[str] = None
    RDSO_WEBHOOK_SECRET: str = "rdso-webhook-secret-key"
    UDM_WEBHOOK_URL: Optional[str] = None
    UDM_WEBHOOK_SECRET: str = "udm-webhook-secret-key"
    TMS_WEBHOOK_URL: Optional[str] = None
    TMS_WEBHOOK_SECRET: str = "tms-webhook-secret-key"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
