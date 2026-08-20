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
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "postgresql+psycopg2://trackchain:trackchain_secret@localhost:5432/trackchain"

    # S3 / MinIO
    S3_ENDPOINT_URL: Optional[str] = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "trackchain-media"
    S3_REGION: str = "us-east-1"

    # Security
    API_KEY_SECRET: str = "trackchain-super-secret-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440


@lru_cache()
def get_settings() -> Settings:
    return Settings()
