"""Celery tasks for email delivery."""
import logging
import uuid

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.integrations.resend import send_email

logger = logging.getLogger(__name__)

BATCH_SIZE = 100


def _append_tracking_pixel(html: str, send_id: str, base_url: str) -> str:
    pixel = f'<img src="{base_url}/track/{send_id}/open.gif" width="1" height="1">'
    if "</body>" in html:
        return html.replace("</body>", f"{pixel}</body>")
    return html + pixel


@celery_app.task(bind=True, max_retries=3)
def send_transactional_email_task(
    self,
    to: str,
    subject: str,
    html_body: str,
    from_email: str | None = None,
    send_id: str | None = None,
    track_opens: bool = False,
) -> str:
    """Send a single transactional email."""
    try:
        settings = get_settings()
        body = html_body
        if track_opens and send_id and settings.frontend_url:
            body = _append_tracking_pixel(body, send_id, settings.frontend_url)
        return send_email(to, subject, body, from_email)
    except Exception as exc:
        logger.exception("Transactional email failed to=%s", to)
        self.retry(countdown=60, exc=exc)
    return ""


@celery_app.task(bind=True, max_retries=3)
def send_campaign_batch_task(
    self,
    batch: list[dict],
    campaign_id: str,
    subject: str,
    html_body: str,
    from_email: str | None = None,
) -> None:
    """Send a batch of campaign emails. Each item: {email, send_id}."""
    settings = get_settings()
    for item in batch:
        try:
            body = html_body
            send_id = item.get("send_id")
            if send_id and settings.frontend_url:
                body = _append_tracking_pixel(body, send_id, settings.frontend_url)
            send_email(item["email"], subject, body, from_email)
        except Exception:
            logger.exception("Campaign email failed to=%s campaign=%s", item["email"], campaign_id)


@celery_app.task(bind=True, max_retries=3)
def send_magic_link_email(
    self,
    email: str,
    token: str,
    tenant_id: str,
) -> None:
    """Send magic link email."""
    try:
        settings = get_settings()
        magic_link_url = f"{settings.frontend_url}/magic-link/verify?token={token}"
        html = f'<p>Click <a href="{magic_link_url}">here</a> to log in.</p>'
        send_email(email, "Your Magic Link", html)
        logger.info("Magic link sent to %s", email)
    except Exception as exc:
        logger.exception("Magic link email failed to=%s", email)
        self.retry(countdown=60, exc=exc)


@celery_app.task(bind=True, max_retries=3)
def send_password_reset_email(
    self,
    email: str,
    token: str,
    tenant_id: str,
) -> None:
    """Send password reset email."""
    try:
        settings = get_settings()
        reset_url = f"{settings.frontend_url}/reset-password?token={token}"
        html = f'<p>Click <a href="{reset_url}">here</a> to reset your password.</p>'
        send_email(email, "Password Reset", html)
        logger.info("Password reset sent to %s", email)
    except Exception as exc:
        logger.exception("Password reset email failed to=%s", email)
        self.retry(countdown=60, exc=exc)


@celery_app.task(bind=True, max_retries=3)
def process_automation_step_task(
    self,
    automation_id: str,
    step_index: int,
    user_id: str,
    trigger_event: str,
) -> None:
    """Evaluate automation step from EmailAutomation.steps JSONB."""
    from app.core.sync_database import get_sync_db
    from app.models.email import EmailAutomation
    from app.models.user import User

    db = get_sync_db()
    try:
        automation = db.get(EmailAutomation, uuid.UUID(automation_id))
        if automation is None or not automation.is_active:
            return

        steps = automation.steps or []
        if step_index >= len(steps):
            return

        step = steps[step_index]
        step_trigger = step.get("trigger_event", "")
        if step_trigger and step_trigger != trigger_event:
            return

        user = db.get(User, uuid.UUID(user_id))
        if user is None:
            return

        html = step.get("template_html", "")
        html = html.replace("{{name}}", user.name or user.email.split("@")[0])

        send_email(user.email, step.get("subject", ""), html)
        logger.info("Automation step sent automation=%s user=%s", automation_id, user_id)
    except Exception as exc:
        logger.exception("Automation step failed automation=%s user=%s", automation_id, user_id)
        self.retry(countdown=60, exc=exc)
    finally:
        db.close()
