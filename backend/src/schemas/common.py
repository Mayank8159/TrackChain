# Base schema contracts and common envelopes for TrackChain (tc.v1).

from datetime import datetime
from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

SCHEMA_VERSION = "tc.v1"


class BaseContractModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class IdempotentRequest(BaseContractModel):
    schema_version: str = Field(default=SCHEMA_VERSION, description="Schema version identifier")
    idempotency_key: str = Field(..., description="Unique idempotency key for network retry deduplication")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Request generation timestamp")


class PaginationParams(BaseContractModel):
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=50, ge=1, le=1000, description="Items per page")


class PaginatedResponse(BaseContractModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
