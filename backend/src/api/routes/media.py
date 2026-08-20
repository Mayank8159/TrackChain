# Issue presigned S3 upload/download URLs for video segments and images.

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from src.services.s3 import (
    generate_presigned_upload_url,
    generate_presigned_download_url,
)

router = APIRouter(prefix="/api/media", tags=["Media"])


class PresignUploadRequest(BaseModel):
    filename: str
    contentType: str


class PresignDownloadRequest(BaseModel):
    s3_key: str


@router.post("/presign-upload")
def get_upload_url(req: PresignUploadRequest):
    """Issue a presigned S3 upload URL for edge video streams and defect crops."""
    try:
        return generate_presigned_upload_url(req.filename, req.contentType)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"S3 generation failed: {exc}")


@router.post("/presign-download")
def get_download_url(req: PresignDownloadRequest):
    """Issue a presigned S3 download URL for viewing media clips."""
    try:
        url = generate_presigned_download_url(req.s3_key)
        return {"download_url": url}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"S3 generation failed: {exc}")
