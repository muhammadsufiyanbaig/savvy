"""S3 download service (read-only for statement-analysis-service)."""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

_s3_client = None


def _get_s3():
    """Return boto3 S3 client; None if AWS not configured / not installed."""
    global _s3_client
    if _s3_client is not None:
        return _s3_client

    from app.core.config import settings

    if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
        return None

    try:
        import boto3

        _s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        logger.info("S3 client initialised")
        return _s3_client
    except Exception as exc:
        logger.warning("S3 client init failed: %s", exc)
        return None


def parse_s3_url(file_url: str) -> Tuple[Optional[str], str]:
    """Parse 's3://bucket/key' → (bucket, key). Falls back to config bucket."""
    from app.core.config import settings

    if file_url.startswith("s3://"):
        without_scheme = file_url[5:]
        parts = without_scheme.split("/", 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ""
        return bucket, key

    return settings.S3_BUCKET_NAME, file_url


def download_statement(file_url: str) -> Optional[bytes]:
    """Download statement from S3 and return raw bytes. Returns None on failure."""
    client = _get_s3()
    if client is None:
        logger.warning("S3 unavailable — cannot download %s", file_url)
        return None

    bucket, key = parse_s3_url(file_url)
    if not key:
        logger.error("Empty S3 key derived from URL: %s", file_url)
        return None

    try:
        import io

        buf = io.BytesIO()
        client.download_fileobj(bucket, key, buf)
        buf.seek(0)
        data = buf.read()
        logger.info("Downloaded %d bytes from s3://%s/%s", len(data), bucket, key)
        return data
    except Exception as exc:
        logger.error("S3 download failed s3://%s/%s: %s", bucket, key, exc)
        return None


def detect_file_type(file_url: str) -> str:
    """Derive 'pdf' | 'csv' | 'excel' from the URL/key extension."""
    lower = file_url.lower().split("?")[0]
    if lower.endswith(".pdf"):
        return "pdf"
    if lower.endswith(".csv"):
        return "csv"
    if lower.endswith((".xlsx", ".xls")):
        return "excel"
    return "unknown"
