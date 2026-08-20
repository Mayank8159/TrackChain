# Issue presigned S3 upload/download URLs and register media assets (tc.v1 SOTA).

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from src.api.deps import get_db_session
from src.db.models import MediaAsset
from src.schemas.media import (
    PresignUploadRequest,
    PresignUploadResponse,
    MediaCompleteRequest,
    PresignDownloadResponse,
    MediaAssetResponse,
)
from src.services.s3 import (
    generate_presigned_upload_url,
    generate_presigned_download_url,
)
from src.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/media", tags=["Media"])


@router.post("/presign-upload", response_model=PresignUploadResponse)
def get_upload_url(
    req: PresignUploadRequest,
    db: Session = Depends(get_db_session),
):
    """Issue a presigned S3 upload URL and create a pending MediaAsset record."""
    try:
        s3_data = generate_presigned_upload_url(req.filename, req.content_type)
        asset = MediaAsset(
            session_id=req.session_id,
            device_id=req.device_id,
            media_type=req.media_type,
            s3_bucket=settings.S3_BUCKET_NAME,
            s3_key=s3_data["s3_key"],
            content_type=req.content_type,
            size_bytes=req.size_bytes or 0,
            chainage_start_m=req.chainage_start_m,
            chainage_end_m=req.chainage_end_m,
            upload_status="pending",
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)

        return PresignUploadResponse(
            media_id=asset.media_id,
            upload_url=s3_data["upload_url"],
            s3_bucket=settings.S3_BUCKET_NAME,
            s3_key=s3_data["s3_key"],
            file_url=s3_data.get("file_url"),
            expires_in_seconds=3600,
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"S3 generation failed: {exc}")


@router.post("/complete", response_model=dict)
def complete_media_upload(
    req: MediaCompleteRequest,
    db: Session = Depends(get_db_session),
):
    """Confirm successful upload of media file to S3."""
    asset = db.query(MediaAsset).filter(MediaAsset.media_id == req.media_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Media asset not found")

    asset.upload_status = req.upload_status
    if req.size_bytes:
        asset.size_bytes = req.size_bytes
    if req.duration_seconds:
        asset.duration_seconds = req.duration_seconds
    if req.checksum:
        asset.checksum = req.checksum

    db.commit()
    return {"status": "ok", "media_id": req.media_id, "upload_status": asset.upload_status}


@router.get("/{media_id}/presign-download", response_model=PresignDownloadResponse)
def get_download_url(
    media_id: str,
    db: Session = Depends(get_db_session),
):
    """Issue a presigned S3 download URL for viewing media clips or defect frames."""
    asset = db.query(MediaAsset).filter(MediaAsset.media_id == media_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Media asset not found")

    try:
        url = generate_presigned_download_url(asset.s3_key)
        return PresignDownloadResponse(
            media_id=asset.media_id,
            download_url=url,
            expires_in_seconds=3600,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"S3 generation failed: {exc}")


@router.get("", response_model=List[MediaAssetResponse])
def list_session_media(
    session_id: str = Query(..., description="Session identifier"),
    media_type: Optional[str] = Query(None),
    db: Session = Depends(get_db_session),
):
    """List all registered media assets (video segments, evidence images) for a session."""
    query = db.query(MediaAsset).filter(MediaAsset.session_id == session_id)
    if media_type:
        query = query.filter(MediaAsset.media_type == media_type)
    return query.order_by(MediaAsset.created_at.desc()).all()
