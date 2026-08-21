# Settings loader (pydantic-settings) reading environment variables.

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # General
    PROJECT_NAME: str = "TrackChain Backend API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False

    # Database (PostgreSQL / TimescaleDB)
    DATABASE_URL: str = "postgresql+psycopg2://trackchain:trackchain_secret@localhost:5432/trackchain"

    # Redis (Rate limiting and caching)
    REDIS_URL: Optional[str] = "redis://localhost:6379/0"

    # S3 / MinIO
    S3_ENDPOINT_URL: Optional[str] = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "trackchain-media"
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
