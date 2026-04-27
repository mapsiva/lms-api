"""Push notification service stub."""
import logging
import uuid

logger = logging.getLogger(__name__)


async def send_push_notification(
    user_id: uuid.UUID,
    title: str,
    body: str,
    action_url: str | None = None,
) -> None:
    """Send a Web Push notification to all subscriptions for a user.

    Raises:
        NotImplementedError: pywebpush is available but full integration not wired yet.
    """
    logger.info(
        "Push notification stub: user=%s title=%s action_url=%s",
        user_id,
        title,
        action_url,
    )
    raise NotImplementedError("send_push_notification is not yet implemented")
