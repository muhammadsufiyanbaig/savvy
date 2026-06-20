"""AWS S3 service — fire-and-forget upload/download for bank statements."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_s3_client = None


def _get_s3():
    """Lazy-init boto3 S3 client — returns None if AWS not configured."""
    global _s3_client
    if _s3_client is not None:
        return _s3_client
    try:
        import boto3
        _s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        return _s3_client
    except Exception as exc:
        logger.warning("S3 client init failed (non-fatal): %s", exc)
        return None


def build_s3_key(user_id: int, file_name: str) -> str:
    """Deterministic S3 key: statements/user_<id>/YYYY/MM/<file_name>."""
    now = datetime.utcnow()
    return f"statements/user_{user_id}/{now:%Y}/{now:%m}/{file_name}"


def upload_file(file_obj, s3_key: str, content_type: str = "application/octet-stream") -> bool:
    """
    Upload file-like object to S3.
    Returns True on success, False on failure (non-fatal).
    """
    s3 = _get_s3()
    if s3 is None:
        logger.warning("S3 not configured — skipping upload for %s", s3_key)
        return False
    try:
        s3.upload_fileobj(
            file_obj,
            settings.AWS_S3_BUCKET,
            s3_key,
            ExtraArgs={"ContentType": content_type},
        )
        logger.info("S3 upload success: %s", s3_key)
        return True
    except Exception as exc:
        logger.error("S3 upload failed for %s: %s", s3_key, exc)
        return False


def generate_presigned_url(s3_key: str, expires_in: int = None) -> Optional[str]:
    """Generate presigned GET URL. Returns None if S3 unavailable."""
    expires_in = expires_in or settings.S3_PRESIGNED_URL_EXPIRES
    s3 = _get_s3()
    if s3 is None:
        return None
    try:
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.AWS_S3_BUCKET, "Key": s3_key},
            ExpiresIn=expires_in,
        )
        return url
    except Exception as exc:
        logger.error("Presigned URL generation failed for %s: %s", s3_key, exc)
        return None


def delete_file(s3_key: str) -> bool:
    """Delete file from S3. Returns True on success."""
    s3 = _get_s3()
    if s3 is None:
        return False
    try:
        s3.delete_object(Bucket=settings.AWS_S3_BUCKET, Key=s3_key)
        logger.info("S3 delete success: %s", s3_key)
        return True
    except Exception as exc:
        logger.error("S3 delete failed for %s: %s", s3_key, exc)
        return False


def get_file_size(file_obj) -> int:
    """Get file size in bytes by seeking to end."""
    file_obj.seek(0, 2)
    size = file_obj.tell()
    file_obj.seek(0)
    return size
