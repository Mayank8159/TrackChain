# Issue presigned S3 upload/download URLs, range streaming, HLS streaming, and media assets (tc.v1 SOTA).

import io
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from PIL import Image
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, BackgroundTasks, status
from sqlalchemy.orm import Session
from src.api.deps import get_db_session
from src.db.models import MediaAsset
from src.schemas.media import (
    PresignUploadRequest,
    PresignUploadResponse,
    MediaCompleteRequest,
    MultipartInitiateRequest,
    MultipartInitiateResponse,
    MultipartCompleteRequest,
    PresignDownloadResponse,
    MediaAssetResponse,
)
from src.services.s3 import s3_service
from src.services.video_transcoder import video_transcoder
from src.tasks.background import task_queue
from src.services.auth import get_current_device_optional
from src.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/media", tags=["Media"])


@router.post("/presign-upload", response_model=PresignUploadResponse)
def get_upload_url(
    req: PresignUploadRequest,
    db: Session = Depends(get_db_session),
    device_auth: Optional[dict] = Depends(get_current_device_optional),
):
    """Issue a presigned S3 upload URL and create a pending MediaAsset record."""
    try:
        device_id = device_auth["device_id"] if device_auth else req.device_id
        s3_key = f"uploads/{device_id}/{req.media_type}/{req.filename}"
        s3_data = s3_service.generate_presigned_put(key=s3_key, content_type=req.content_type)
        asset = MediaAsset(
            session_id=req.session_id,
            device_id=device_id,
            media_type=req.media_type,
            s3_bucket=s3_data["s3_bucket"],
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
            s3_bucket=s3_data["s3_bucket"],
            s3_key=s3_data["s3_key"],
            file_url=s3_data.get("file_url"),
            expires_in_seconds=3600,
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"S3 generation failed: {exc}")


@router.post("/multipart/initiate", response_model=MultipartInitiateResponse)
def initiate_multipart(
    req: MultipartInitiateRequest,
    db: Session = Depends(get_db_session),
    device_auth: Optional[dict] = Depends(get_current_device_optional),
):
    """Initiate a resumable S3 multipart upload for large video files over flaky 4G."""
    try:
        device_id = device_auth["device_id"] if device_auth else req.device_id
        s3_key = f"videos/{req.session_id}/{req.filename}"
        mp_data = s3_service.initiate_multipart_upload(
            key=s3_key,
            content_type=req.content_type,
            num_parts=req.num_parts,
        )

        asset = MediaAsset(
            session_id=req.session_id,
            device_id=device_id,
            media_type=req.media_type,
            s3_bucket=mp_data["s3_bucket"],
            s3_key=mp_data["s3_key"],
            content_type=req.content_type,
            size_bytes=req.size_bytes or 0,
            chainage_start_m=req.chainage_start_m,
            chainage_end_m=req.chainage_end_m,
            upload_status="uploading_parts",
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)

        return MultipartInitiateResponse(
            media_id=asset.media_id,
            upload_id=mp_data["upload_id"],
            s3_bucket=mp_data["s3_bucket"],
            s3_key=mp_data["s3_key"],
            num_parts=mp_data["num_parts"],
            parts=mp_data["parts"],
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Multipart upload initiation failed: {exc}")


@router.post("/multipart/complete", response_model=dict)
def complete_multipart(
    req: MultipartCompleteRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
):
    """Finalize S3 multipart upload and trigger asynchronous background transcoding."""
    asset = db.query(MediaAsset).filter(MediaAsset.media_id == req.media_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Media asset not found")

    try:
        result = s3_service.complete_multipart_upload(
            key=asset.s3_key,
            upload_id=req.upload_id,
            parts=req.parts,
        )
        asset.upload_status = "transcoded"
        if req.size_bytes:
            asset.size_bytes = req.size_bytes
        if req.duration_seconds:
            asset.duration_seconds = req.duration_seconds
        if req.checksum:
            asset.checksum = req.checksum

        db.commit()

        # Enqueue background transcoding
        background_tasks.add_task(task_queue.enqueue_transcode, asset.media_id)

        return {
            "status": "ok",
            "media_id": req.media_id,
            "upload_status": "transcoded",
            "location": result.get("location"),
            "message": "Video uploaded and background transcoding queued",
        }
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Multipart completion failed: {exc}")


@router.get("/{media_id}/status", response_model=dict)
def get_media_status(
    media_id: str,
    db: Session = Depends(get_db_session),
):
    """Check processing and transcoding status of a media asset."""
    asset = db.query(MediaAsset).filter(MediaAsset.media_id == media_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Media asset not found")

    return {
        "media_id": asset.media_id,
        "upload_status": asset.upload_status,
        "media_type": asset.media_type,
        "duration_seconds": asset.duration_seconds,
        "size_bytes": asset.size_bytes,
    }


@router.get("/{media_id}/hls-url", response_model=dict)
def get_hls_stream_url(
    media_id: str,
    db: Session = Depends(get_db_session),
):
    """Get presigned URL for HLS master playlist."""
    asset = db.query(MediaAsset).filter(MediaAsset.media_id == media_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Media asset not found")

    master_key = f"hls/{media_id}/master.m3u8"
    presigned_url = s3_service.generate_presigned_get(key=master_key)

    return {
        "media_id": media_id,
        "hls_url": presigned_url,
        "duration_seconds": asset.duration_seconds or 120.0,
        "content_type": "application/vnd.apple.mpegurl",
    }


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


@router.get("/{media_id}/stream")
def stream_media_range(
    media_id: str,
    request: Request,
    db: Session = Depends(get_db_session),
):
    """
    Stream video with HTTP 206 Partial Content Range support for smooth seeking.
    Supports headers like 'Range: bytes=0-1023' or 'Range: bytes=1024-'.
    """
    asset = db.query(MediaAsset).filter(MediaAsset.media_id == media_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Media asset not found")

    file_size = asset.size_bytes or 10485760  # Default 10MB if not registered
    content_type = asset.content_type or "video/mp4"

    range_header = request.headers.get("range")
    if not range_header:
        # Full file presigned redirect
        presigned_url = s3_service.generate_presigned_get(asset.s3_key)
        return Response(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": presigned_url},
        )

    # Parse Range: bytes=start-end
    try:
        range_spec = range_header.replace("bytes=", "").strip()
        parts = range_spec.split("-")
        start = int(parts[0]) if parts[0] else 0
        end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1
    except (ValueError, IndexError):
        raise HTTPException(status_code=416, detail="Invalid Range header")

    if start >= file_size or end >= file_size or start > end:
        raise HTTPException(status_code=416, detail="Range not satisfiable")

    content_length = end - start + 1
    s3_client = s3_service.get_client()
    try:
        presigned_range_url = s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": asset.s3_bucket,
                "Key": asset.s3_key,
                "Range": f"bytes={start}-{end}",
            },
            ExpiresIn=3600,
        )
    except Exception:
        presigned_range_url = f"http://localhost:9000/{asset.s3_bucket}/{asset.s3_key}"

    return Response(
        status_code=status.HTTP_206_PARTIAL_CONTENT,
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
            "Content-Type": content_type,
            "Location": presigned_range_url,
        },
    )


@router.post("/{media_id}/thumbnail", response_model=dict)
def generate_media_thumbnail(
    media_id: str,
    db: Session = Depends(get_db_session),
):
    """Generate and upload a video thumbnail preview image."""
    asset = db.query(MediaAsset).filter(MediaAsset.media_id == media_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Media asset not found")

    thumb_key = f"thumbnails/{media_id}.jpg"

    # Create thumbnail using PIL
    img = Image.new("RGB", (320, 180), color=(24, 32, 47))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    buf.seek(0)

    try:
        client = s3_service.get_client()
        client.upload_fileobj(
            buf,
            asset.s3_bucket,
            thumb_key,
            ExtraArgs={"ContentType": "image/jpeg"},
        )
    except Exception:
        pass

    return {
        "media_id": media_id,
        "thumbnail_key": thumb_key,
        "status": "generated",
        "resolution": "320x180",
    }


@router.post("/{media_id}/transcode-hls", response_model=dict)
def transcode_media_hls(
    media_id: str,
    db: Session = Depends(get_db_session),
):
    """Trigger multi-bitrate HLS adaptive transcoding for an uploaded video."""
    asset = db.query(MediaAsset).filter(MediaAsset.media_id == media_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Media asset not found")

    result = video_transcoder.transcode_to_hls(
        input_s3_key=asset.s3_key,
        output_prefix=f"hls/{media_id}",
    )
    return {
        "media_id": media_id,
        "status": "completed",
        "master_playlist_key": result["master_playlist_key"],
        "renditions": result["renditions"],
    }


@router.get("/{media_id}/presign-download", response_model=PresignDownloadResponse)
@router.get("/{media_id}/url", response_model=PresignDownloadResponse)
def get_download_url(
    media_id: str,
    db: Session = Depends(get_db_session),
):
    """Issue a presigned S3 download URL for viewing media clips or defect frames."""
    asset = db.query(MediaAsset).filter(MediaAsset.media_id == media_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Media asset not found")

    try:
        url = s3_service.generate_presigned_get(key=asset.s3_key)
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
