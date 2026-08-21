# S3 / MinIO service: single-part presigned URLs & resumable multipart uploads (tc.v1 SOTA).

import os
from typing import Dict, Any, List, Optional
import boto3
from botocore.client import Config
from src.config import get_settings

settings = get_settings()


class S3Service:
    """
    Production S3-compatible service for video streams, evidence images, and media assets.
    Compatible with local MinIO in development and AWS S3 in cloud production.
    """

    def __init__(self):
        self.endpoint_url = settings.S3_ENDPOINT_URL
        self.access_key = settings.S3_ACCESS_KEY
        self.secret_key = settings.S3_SECRET_KEY
        self.bucket = settings.S3_BUCKET_NAME
        self.region = settings.S3_REGION

    def get_client(self):
        """Instantiate configured boto3 S3 client with Signature Version 4 and fast failover."""
        return boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
            config=Config(
                signature_version="s3v4",
                connect_timeout=1,
                read_timeout=1,
                retries={"max_attempts": 1},
            ),
        )

    def generate_presigned_put(
        self,
        key: str,
        content_type: str = "video/mp4",
        expires_in: int = 3600,
    ) -> Dict[str, str]:
        """Generate a presigned PUT URL for direct edge device upload."""
        s3 = self.get_client()
        url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": self.bucket,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=expires_in,
        )
        base_endpoint = self.endpoint_url or f"https://s3.{self.region}.amazonaws.com"
        return {
            "upload_url": url,
            "s3_bucket": self.bucket,
            "s3_key": key,
            "file_url": f"{base_endpoint}/{self.bucket}/{key}",
        }

    def generate_presigned_get(
        self,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        """Generate a presigned GET URL for secure frontend media streaming."""
        s3 = self.get_client()
        return s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    def initiate_multipart_upload(
        self,
        key: str,
        content_type: str = "video/mp4",
        num_parts: int = 100,
        expires_in: int = 86400,
    ) -> Dict[str, Any]:
        """
        Initiates a resumable S3 multipart upload for large video files over flaky 4G networks.
        Generates presigned URLs for each part (e.g. 100 parts of 5MB = up to 500MB video).
        """
        s3 = self.get_client()
        response = s3.create_multipart_upload(
            Bucket=self.bucket,
            Key=key,
            ContentType=content_type,
        )
        upload_id = response["UploadId"]

        part_urls = []
        for part_num in range(1, num_parts + 1):
            url = s3.generate_presigned_url(
                ClientMethod="upload_part",
                Params={
                    "Bucket": self.bucket,
                    "Key": key,
                    "UploadId": upload_id,
                    "PartNumber": part_num,
                },
                ExpiresIn=expires_in,
            )
            part_urls.append({"part_number": part_num, "upload_url": url})

        return {
            "upload_id": upload_id,
            "s3_bucket": self.bucket,
            "s3_key": key,
            "num_parts": num_parts,
            "parts": part_urls,
        }

    def complete_multipart_upload(
        self,
        key: str,
        upload_id: str,
        parts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Finalizes multipart upload by assembling uploaded parts in S3.
        parts format: [{"PartNumber": 1, "ETag": "..."}]
        """
        s3 = self.get_client()
        # Ensure correct uppercase formatting for boto3
        formatted_parts = [
            {
                "PartNumber": p.get("PartNumber") or p.get("part_number"),
                "ETag": p.get("ETag") or p.get("etag"),
            }
            for p in parts
        ]
        # Sort parts by PartNumber ascending as required by S3 API
        formatted_parts = sorted(formatted_parts, key=lambda x: x["PartNumber"])

        response = s3.complete_multipart_upload(
            Bucket=self.bucket,
            Key=key,
            UploadId=upload_id,
            MultipartUpload={"Parts": formatted_parts},
        )
        base_endpoint = self.endpoint_url or f"https://s3.{self.region}.amazonaws.com"
        return {
            "status": "completed",
            "s3_bucket": self.bucket,
            "s3_key": key,
            "location": response.get("Location", f"{base_endpoint}/{self.bucket}/{key}"),
        }

    def abort_multipart_upload(self, key: str, upload_id: str):
        """Aborts an in-progress multipart upload and deletes temporary chunk parts."""
        s3 = self.get_client()
        s3.abort_multipart_upload(
            Bucket=self.bucket,
            Key=key,
            UploadId=upload_id,
        )


# Global singleton instance
s3_service = S3Service()


# Top-level functional compatibility helpers
def get_s3_client():
    return s3_service.get_client()


def generate_presigned_upload_url(
    filename: str,
    content_type: str = "video/mp4",
    expires_in: int = 3600,
) -> Dict[str, str]:
    key = f"uploads/{filename}" if not filename.startswith("uploads/") else filename
    return s3_service.generate_presigned_put(key=key, content_type=content_type, expires_in=expires_in)


def generate_presigned_download_url(s3_key: str, expires_in: int = 3600) -> str:
    return s3_service.generate_presigned_get(key=s3_key, expires_in=expires_in)
