"""AI moderation Celery task."""
import logging
import uuid

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2)
def moderate_content_task(self, post_id: str | None = None, comment_id: str | None = None) -> dict:
    """Call Claude Haiku to moderate content. Create Report if flagged."""
    import asyncio

    from app.core.sync_database import get_sync_db
    from app.integrations.anthropic import AnthropicClient
    from app.models.community import Comment, Post, Report

    db = get_sync_db()
    try:
        item: Post | Comment | None = None
        text = ""
        tenant_id = None

        if post_id:
            item = db.get(Post, uuid.UUID(post_id))
            if item:
                text = item.body
                tenant_id = item.tenant_id
        elif comment_id:
            item = db.get(Comment, uuid.UUID(comment_id))
            if item:
                text = item.body
                tenant_id = item.tenant_id

        if not item or not text:
            logger.warning("No content to moderate post=%s comment=%s", post_id, comment_id)
            return {"flagged": False, "reason": "no content"}

        client = AnthropicClient()
        result = asyncio.run(client.moderate_content(text))

        if result.flagged:
            report = Report(
                tenant_id=tenant_id,
                post_id=uuid.UUID(post_id) if post_id else None,
                comment_id=uuid.UUID(comment_id) if comment_id else None,
                reporter_id=None,  # AI flagged
                reason=result.reason,
                ai_flagged=True,
            )
            db.add(report)
            db.commit()
            logger.info("AI flagged content post=%s comment=%s", post_id, comment_id)

        return {"flagged": result.flagged, "score": result.score, "reason": result.reason}
    except Exception as exc:
        logger.exception("Moderation task failed")
        self.retry(countdown=60, exc=exc)
    finally:
        db.close()
    return {"flagged": False, "reason": "error"}
