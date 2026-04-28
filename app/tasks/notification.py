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
    """Dispatch a broadcast notification via Redis pub/sub + Web Push."""
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

            # Web Push for each user
            dispatch_push_notification_task.delay(uid, tenant_id, title, body, None)

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


@celery_app.task(bind=True, max_retries=2)
def dispatch_push_notification_task(
    self,
    user_id: str,
    tenant_id: str,
    title: str,
    body: str | None = None,
    action_url: str | None = None,
) -> None:
    """Send Web Push to all active subscriptions for a user."""
    settings = get_settings()
    if not settings.vapid_private_key:
        logger.debug("VAPID not configured, skipping push for user=%s", user_id)
        return

    try:
        from pywebpush import WebPushException, webpush  # type: ignore[import-untyped]
    except ImportError:
        logger.warning("pywebpush not installed, skipping push")
        return

    db = get_sync_db()
    try:
        from sqlalchemy import select

        from app.models.push_subscription import PushSubscription

        uid = uuid.UUID(user_id)
        subs = db.execute(
            select(PushSubscription).where(PushSubscription.user_id == uid)
        ).scalars().all()

        if not subs:
            return

        payload = json.dumps(
            {"title": title, "body": body, "action_url": action_url}
        )
        vapid_claims = {"sub": f"mailto:{settings.vapid_claims_email}"}
        stale_ids: list[uuid.UUID] = []

        for sub in subs:
            try:
                webpush(
                    subscription_info={
                        "endpoint": sub.endpoint,
                        "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                    },
                    data=payload,
                    vapid_private_key=settings.vapid_private_key,
                    vapid_claims=vapid_claims,
                )
            except WebPushException as exc:
                status = getattr(exc.response, "status_code", None)
                if status in (404, 410):
                    # Subscription expired or unregistered — prune it
                    stale_ids.append(sub.id)
                    logger.info("Pruning stale push sub=%s status=%s", sub.id, status)
                else:
                    logger.warning("WebPush failed sub=%s: %s", sub.id, exc)

        if stale_ids:
            from sqlalchemy import delete

            db.execute(
                delete(PushSubscription).where(PushSubscription.id.in_(stale_ids))
            )
            db.commit()

        logger.debug("Push sent user=%s subs=%d stale=%d", user_id, len(subs), len(stale_ids))
    except Exception as exc:
        logger.exception("dispatch_push_notification_task failed user=%s", user_id)
        self.retry(countdown=30, exc=exc)
    finally:
        db.close()
