# Pydantic schemas for S3 media asset upload/download contracts (tc.v1).

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import Field, ConfigDict
from src.schemas.common import BaseContractModel


class PresignUploadRequest(BaseContractModel):
    session_id: str
    device_id: Optional[str] = None
    media_type: str = Field(..., description="video_segment, evidence_image, thumbnail, report_file")
    filename: str = Field(..., description="Original or generated file name")
    content_type: str = Field(default="video/mp4", description="MIME content type, e.g. video/mp4, image/jpeg")
    size_bytes: Optional[int] = Field(default=0)
    chainage_start_m: Optional[float] = None
    chainage_end_m: Optional[float] = None


class PresignUploadResponse(BaseContractModel):
    media_id: str
    upload_url: str
    s3_bucket: str
    s3_key: str
    file_url: Optional[str] = None
    expires_in_seconds: int = Field(default=3600)


class MultipartPartItem(BaseContractModel):
    model_config = ConfigDict(populate_by_name=True)

    part_number: int = Field(..., alias="PartNumber")
    upload_url: Optional[str] = None
    etag: Optional[str] = Field(None, alias="ETag")


class MultipartInitiateRequest(BaseContractModel):
    session_id: str
    device_id: Optional[str] = None
    media_type: str = Field(default="video_segment")
    filename: str
    content_type: str = Field(default="video/mp4")
    num_parts: int = Field(default=20, ge=1, le=1000)
    size_bytes: Optional[int] = Field(default=0)
    chainage_start_m: Optional[float] = None
    chainage_end_m: Optional[float] = None


class MultipartInitiateResponse(BaseContractModel):
    media_id: str
    upload_id: str
    s3_bucket: str
    s3_key: str
    num_parts: int
    parts: List[Dict[str, Any]]


class MultipartCompleteRequest(BaseContractModel):
    media_id: str
    upload_id: str
    parts: List[Dict[str, Any]] = Field(..., description="List of dicts with part_number/PartNumber and etag/ETag")
    size_bytes: Optional[int] = None
    duration_seconds: Optional[float] = None
    checksum: Optional[str] = None


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
