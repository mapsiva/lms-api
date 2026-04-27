"""Cloudflare R2 integration using the S3-compatible API."""
import asyncio
import logging
from functools import partial

from app.core.config import get_settings

logger = logging.getLogger(__name__)

try:
    import boto3  # type: ignore[import-untyped]
    from botocore.client import BaseClient  # type: ignore[import-untyped]
    _BOTO3_AVAILABLE = True
except ImportError:  # pragma: no cover
    _BOTO3_AVAILABLE = False
    BaseClient = object  # type: ignore[misc,assignment]


def _get_s3_client() -> "BaseClient":
    if not _BOTO3_AVAILABLE:
        raise NotImplementedError(
            "boto3 is not installed. Install it to use R2 storage integration."
        )
    settings = get_settings()
    endpoint_url = settings.r2_endpoint_url
    if not endpoint_url:
        raise RuntimeError("R2_ENDPOINT_URL is not configured")
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.r2_access_key_id.get_secret_value(),
        aws_secret_access_key=settings.r2_secret_access_key.get_secret_value(),
    )


def _public_url(key: str) -> str:
    settings = get_settings()
    base = settings.r2_public_url
    if not base:
        raise RuntimeError("R2_PUBLIC_URL is not configured")
    return f"{base.rstrip('/')}/{key}"


def _bucket_name() -> str:
    settings = get_settings()
    bucket = settings.r2_bucket_name
    if not bucket:
        raise RuntimeError("R2_BUCKET_NAME is not configured")
    return bucket


async def upload_file(file_content: bytes, key: str, content_type: str) -> str:
    """Upload bytes to R2 and return the public URL."""
    client = _get_s3_client()
    bucket = _bucket_name()

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        partial(
            client.put_object,
            Bucket=bucket,
            Key=key,
            Body=file_content,
            ContentType=content_type,
        ),
    )
    url = _public_url(key)
    logger.info("Uploaded to R2 key=%s url=%s", key, url)
    return url


async def delete_file(key: str) -> None:
    """Delete an object from R2 by key."""
    client = _get_s3_client()
    bucket = _bucket_name()

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        partial(client.delete_object, Bucket=bucket, Key=key),
    )
    logger.info("Deleted from R2 key=%s", key)
