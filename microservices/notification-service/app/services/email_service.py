"""Email delivery via SMTP — lazy init, non-fatal."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)

# ── HTML templates ─────────────────────────────────────────────────────────────

_GENERIC_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head><style>
  body{{font-family:Arial,sans-serif;line-height:1.6;color:#333;}}
  .wrap{{max-width:600px;margin:0 auto;padding:20px;}}
  .hdr{{background:#2563eb;color:#fff;padding:20px;border-radius:8px 8px 0 0;}}
  .body{{background:#f8fafc;padding:20px;border-radius:0 0 8px 8px;}}
  .footer{{text-align:center;padding:12px;color:#888;font-size:12px;}}
</style></head>
<body>
<div class="wrap">
  <div class="hdr"><h2>{title}</h2></div>
  <div class="body"><p>{message}</p></div>
  <div class="footer">Savvy — Your Personal Finance Assistant</div>
</div>
</body>
</html>"""

_BUDGET_ALERT_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head><style>
  body{{font-family:Arial,sans-serif;line-height:1.6;color:#333;}}
  .wrap{{max-width:600px;margin:0 auto;padding:20px;}}
  .hdr{{background:#dc2626;color:#fff;padding:20px;border-radius:8px 8px 0 0;}}
  .body{{background:#fef2f2;padding:20px;border-radius:0 0 8px 8px;}}
  .alert{{background:#fee2e2;border-left:4px solid #dc2626;padding:15px;margin:15px 0;}}
  .footer{{text-align:center;padding:12px;color:#888;font-size:12px;}}
</style></head>
<body>
<div class="wrap">
  <div class="hdr"><h2>⚠️ Budget Alert</h2></div>
  <div class="body">
    <div class="alert"><strong>{title}</strong></div>
    <p>{message}</p>
  </div>
  <div class="footer">Savvy — Your Personal Finance Assistant</div>
</div>
</body>
</html>"""

_GOAL_COMPLETED_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head><style>
  body{{font-family:Arial,sans-serif;line-height:1.6;color:#333;}}
  .wrap{{max-width:600px;margin:0 auto;padding:20px;}}
  .hdr{{background:#16a34a;color:#fff;padding:20px;text-align:center;border-radius:8px 8px 0 0;}}
  .body{{background:#f0fdf4;padding:20px;border-radius:0 0 8px 8px;}}
  .footer{{text-align:center;padding:12px;color:#888;font-size:12px;}}
</style></head>
<body>
<div class="wrap">
  <div class="hdr"><div style="font-size:48px;">🎉</div><h2>Goal Achieved!</h2></div>
  <div class="body"><p>{message}</p></div>
  <div class="footer">Savvy — Your Personal Finance Assistant</div>
</div>
</body>
</html>"""


def _get_template(notification_type: str, title: str, message: str) -> str:
    if notification_type == "budget":
        return _BUDGET_ALERT_TEMPLATE.format(title=title, message=message)
    if notification_type == "goal":
        return _GOAL_COMPLETED_TEMPLATE.format(title=title, message=message)
    return _GENERIC_TEMPLATE.format(title=title, message=message)


def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
) -> bool:
    """Send email via SMTP. Returns True on success, False on any failure."""
    from app.core.config import settings

    if not settings.SMTP_HOST or not settings.SMTP_USERNAME:
        logger.debug("SMTP not configured — email skipped for %s", to_email)
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = to_email

        if text_content:
            msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, to_email, msg.as_string())

        logger.info("Email sent to %s: %s", to_email, subject)
        return True

    except Exception as exc:
        logger.warning("Email send failed to %s: %s", to_email, exc)
        return False


def send_notification_email(
    to_email: str,
    notification_type: str,
    title: str,
    message: str,
) -> bool:
    """Render template and send."""
    html = _get_template(notification_type, title, message)
    return send_email(to_email, title, html, text_content=message)
