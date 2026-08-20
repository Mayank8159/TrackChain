# S3 client: presigned URLs, bucket checks; works with AWS or MinIO.

import boto3
from botocore.client import Config
from src.config import get_settings

settings = get_settings()


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
        config=Config(signature_version="s3v4"),
    )


def generate_presigned_upload_url(
    filename: str, content_type: str, expires_in: int = 3600
) -> dict:
    """Generate a presigned PUT URL for uploading video clips or defect images."""
    s3 = get_s3_client()
    key = f"uploads/{filename}"
    url = s3.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": settings.S3_BUCKET_NAME,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=expires_in,
    )
    return {
        "upload_url": url,
        "s3_key": key,
        "file_url": f"{settings.S3_ENDPOINT_URL}/{settings.S3_BUCKET_NAME}/{key}",
    }


def generate_presigned_download_url(s3_key: str, expires_in: int = 3600) -> str:
    """Generate a presigned GET URL for downloading or streaming media."""
    s3 = get_s3_client()
    return s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": settings.S3_BUCKET_NAME, "Key": s3_key},
        ExpiresIn=expires_in,
    )
