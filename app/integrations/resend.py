"""Resend email integration."""
import logging

import resend

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, html_body: str, from_email: str | None = None) -> str:
    """Send single email via Resend. Returns send ID or raises on failure."""
    settings = get_settings()
    api_key = settings.resend_api_key.get_secret_value()
    if not api_key:
        raise RuntimeError("RESEND_API_KEY not configured")

    resend.api_key = api_key
    _from = from_email or settings.resend_from_email
    params: resend.Emails.SendParams = {
        "from": _from,
        "to": [to],
        "subject": subject,
        "html": html_body,
    }
    resp = resend.Emails.send(params)
    send_id = resp.get("id", "")
    logger.info("Email sent to=%s id=%s", to, send_id)
    return send_id
