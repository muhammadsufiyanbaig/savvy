"""OneSignal push notifications — lazy init, non-fatal."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_ONESIGNAL_URL = "https://onesignal.com/api/v1/notifications"


def send_push(
    player_ids: List[str],
    title: str,
    message: str,
    data: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Send push notification via OneSignal. Returns external_id or None on failure."""
    from app.core.config import settings

    if not settings.ONESIGNAL_APP_ID or not settings.ONESIGNAL_API_KEY:
        logger.debug("OneSignal not configured — push skipped")
        return None

    if not player_ids:
        logger.debug("No device tokens — push skipped")
        return None

    try:
        import requests

        payload = {
            "app_id": settings.ONESIGNAL_APP_ID,
            "include_player_ids": player_ids,
            "headings": {"en": title},
            "contents": {"en": message},
            "data": data or {},
        }
        headers = {
            "Authorization": f"Basic {settings.ONESIGNAL_API_KEY}",
            "Content-Type": "application/json",
        }
        resp = requests.post(_ONESIGNAL_URL, json=payload, headers=headers, timeout=10)
        if resp.status_code == 200:
            external_id = resp.json().get("id")
            logger.info("Push sent: %s → %s devices", external_id, len(player_ids))
            return external_id
        else:
            logger.warning("OneSignal returned %s: %s", resp.status_code, resp.text[:200])
            return None
    except Exception as exc:
        logger.warning("Push send failed: %s", exc)
        return None
