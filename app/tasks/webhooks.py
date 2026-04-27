import logging
import uuid
from typing import Any

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.core.sync_database import get_sync_db
from app.models.enrollment import Enrollment
from app.models.product import Product
from app.models.user import User
from app.models.webhook import WebhookLog

logger = logging.getLogger(__name__)

BACKOFF_DELAYS = [60, 300, 1800]  # seconds


@celery_app.task(bind=True, max_retries=3)
def process_webhook_task(
    self,
    log_id: str,
    tenant_id: str,
    provider: str,
    event_type: str,
    product_id: str | None,
    buyer_email: str | None,
    buyer_name: str | None,
    status: str,
    raw_payload: dict[str, Any],
) -> None:
    settings = get_settings()
    if settings.webhook_test_mode:
        logger.info("Webhook test mode: skipping enrollment creation for log %s", log_id)
        return

    db = get_sync_db()
    try:
        _process_webhook(
            db,
            log_id,
            tenant_id,
            provider,
            event_type,
            product_id,
            buyer_email,
            buyer_name,
            status,
            raw_payload,
        )
    except Exception as exc:
        logger.exception("Webhook processing failed for log %s", log_id)
        # Update log with error
        try:
            log = db.get(WebhookLog, uuid.UUID(log_id))
            if log:
                log.error_message = str(exc)
                log.attempts = (log.attempts or 0) + 1
                db.commit()
        except Exception:
            pass

        if self.request.retries < len(BACKOFF_DELAYS):
            self.retry(countdown=BACKOFF_DELAYS[self.request.retries], exc=exc)
        else:
            raise
    finally:
        db.close()


def _process_webhook(
    db,
    log_id: str,
    tenant_id: str,
    provider: str,
    event_type: str,
    product_id: str | None,
    buyer_email: str | None,
    buyer_name: str | None,
    status: str,
    raw_payload: dict[str, Any],
) -> None:
    from sqlalchemy import select, update

    tid = uuid.UUID(tenant_id)

    # Mark log as processed
    log = db.get(WebhookLog, uuid.UUID(log_id))
    if log:
        log.processed = True
        log.attempts = (log.attempts or 0) + 1
        db.commit()

    if not product_id or not buyer_email:
        logger.warning("Missing product_id or buyer_email in webhook log %s", log_id)
        return

    # Find product by gateway_id
    product_query = (
        select(Product)
        .where(Product.tenant_id == tid)
        .where(Product.gateway_ids.isnot(None))
        .where(Product.gateway_ids[provider].astext == product_id)
    )
    product = db.execute(product_query).scalar_one_or_none()
    if not product:
        logger.warning("Product not found for %s gateway_id=%s tenant=%s", provider, product_id, tenant_id)
        return

    # Find or create user
    user_query = select(User).where(User.tenant_id == tid, User.email == buyer_email)
    user = db.execute(user_query).scalar_one_or_none()
    if not user:
        user = User(
            id=uuid.uuid4(),
            tenant_id=tid,
            email=buyer_email,
            name=buyer_name or buyer_email.split("@")[0],
            role="student",
            is_active=True,
            is_suspended=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    if status in ("refunded", "cancelled"):
        # Update existing enrollment to refunded/cancelled
        db.execute(
            update(Enrollment)
            .where(Enrollment.tenant_id == tid)
            .where(Enrollment.user_id == user.id)
            .where(Enrollment.product_id == product.id)
            .values(status=status)
        )
        db.commit()
        return

    # Upsert enrollment (active)
    existing_query = (
        select(Enrollment)
        .where(Enrollment.tenant_id == tid)
        .where(Enrollment.user_id == user.id)
        .where(Enrollment.product_id == product.id)
    )
    existing = db.execute(existing_query).scalar_one_or_none()
    if existing:
        if existing.status != "active":
            existing.status = "active"
            db.commit()
    else:
        enrollment = Enrollment(
            tenant_id=tid,
            user_id=user.id,
            product_id=product.id,
            status="active",
            enrolled_by="webhook",
        )
        db.add(enrollment)
        db.commit()
