"""Structured audit logger — append-only event trail for security-critical actions."""

import json
import logging
import time
from typing import Any, Dict, Optional

_audit = logging.getLogger("savvy.audit")


def log(
    action: str,
    *,
    user_id: Optional[int] = None,
    ip: str = "unknown",
    resource_type: str = "",
    resource_id: Any = "",
    success: bool = True,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Emit a single structured audit line.

    Each call produces one JSON log line consumed by the audit logger.
    In production, point the 'savvy.audit' logger at a separate file or
    a log aggregator (CloudWatch, Loki, Splunk) with no rotation-discard.

    All fields safe for logging — do NOT pass raw PII; use user_id (int) only.
    """
    entry: Dict[str, Any] = {
        "ts": int(time.time()),
        "action": action,
        "success": success,
        "ip": ip,
    }
    if user_id is not None:
        entry["user_id"] = user_id
    if resource_type:
        entry["resource_type"] = resource_type
    if resource_id:
        entry["resource_id"] = str(resource_id)
    if extra:
        entry.update({k: v for k, v in extra.items() if k not in entry})

    _audit.info(json.dumps(entry))
