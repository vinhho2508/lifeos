import boto3

from src.core.database import settings


def s3_client():
    """S3 or S3-compatible (R2) client; keys from settings (.env), else boto3's default chain."""
    keys = {}
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        keys = {
            "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
        }
    return boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        endpoint_url=settings.S3_ENDPOINT_URL or None,
        **keys,
    )
