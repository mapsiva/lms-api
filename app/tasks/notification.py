"""Celery tasks for notifications."""
import json
import logging
import uuid
from datetime import datetime, timezone

from redis import Redis as SyncRedis

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.core.sync_database import get_sync_db
from app.models.user import User

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def dispatch_broadcast_notification_task(
    self,
    tenant_id: str,
    notification_id: str,
    title: str,
    body: str | None,
    notification_type: str,
) -> None:
    """Dispatch a broadcast notification via Redis pub/sub and push."""
    db = get_sync_db()
    try:
        tid = uuid.UUID(tenant_id)

        from sqlalchemy import select

        stmt = select(User.id).where(User.tenant_id == tid)
        user_ids = [str(r) for r in db.execute(stmt).scalars().all()]

        settings = get_settings()
        redis: SyncRedis | None = None
        if settings.redis_url:
            redis = SyncRedis.from_url(settings.redis_url, decode_responses=True)

        payload = {
            "id": notification_id,
            "type": notification_type,
            "title": title,
            "body": body,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        for uid in user_ids:
            if redis:
                try:
                    redis.publish(
                        f"notifications:{tid}:{uid}",
                        json.dumps(payload),
                    )
                except Exception:
                    logger.exception("Redis publish failed for user %s", uid)

        logger.info(
            "Broadcast notification dispatched notification=%s users=%d",
            notification_id,
            len(user_ids),
        )
    except Exception as exc:
        logger.exception("Broadcast dispatch failed notification=%s", notification_id)
        self.retry(countdown=60, exc=exc)
    finally:
        db.close()
        if redis:
            redis.close()
