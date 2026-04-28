"""Push notification service."""
import logging
import uuid

logger = logging.getLogger(__name__)


async def send_push_notification(
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    title: str,
    body: str | None = None,
    action_url: str | None = None,
) -> None:
    """Dispatch Web Push to all subscriptions for a user via Celery."""
    from app.tasks.notification import dispatch_push_notification_task

    dispatch_push_notification_task.delay(
        str(user_id),
        str(tenant_id),
        title,
        body,
        action_url,
    )
    logger.debug("Push notification queued user=%s title=%s", user_id, title)
