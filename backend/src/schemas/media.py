# Pydantic schemas for S3 media asset upload/download contracts (tc.v1).

from datetime import datetime
from typing import Optional
from pydantic import Field
from src.schemas.common import BaseContractModel


class PresignUploadRequest(BaseContractModel):
    session_id: str
    device_id: Optional[str] = None
    media_type: str = Field(..., description="video_segment, evidence_image, thumbnail, report_file")
    filename: str = Field(..., description="Original or generated file name")
    content_type: str = Field(..., description="MIME content type, e.g. video/mp4, image/jpeg")
    size_bytes: Optional[int] = Field(default=0)
    chainage_start_m: Optional[float] = None
    chainage_end_m: Optional[float] = None


class PresignUploadResponse(BaseContractModel):
    media_id: str
    upload_url: str
    s3_bucket: str
    s3_key: str
    expires_in_seconds: int = Field(default=3600)


class MediaCompleteRequest(BaseContractModel):
    media_id: str
    size_bytes: Optional[int] = None
    duration_seconds: Optional[float] = None
    checksum: Optional[str] = None
    upload_status: str = Field(default="uploaded", description="uploaded, failed")


class PresignDownloadResponse(BaseContractModel):
    media_id: str
    download_url: str
    expires_in_seconds: int = Field(default=3600)


class MediaAssetResponse(BaseContractModel):
    media_id: str
    session_id: str
    device_id: Optional[str] = None
    segment_id: Optional[str] = None
    media_type: str
    s3_bucket: str
    s3_key: str
    content_type: str
    size_bytes: int
    duration_seconds: Optional[float] = None
    timestamp_start: Optional[datetime] = None
    timestamp_end: Optional[datetime] = None
    chainage_start_m: Optional[float] = None
    chainage_end_m: Optional[float] = None
    upload_status: str
    checksum: Optional[str] = None
    created_at: datetime
