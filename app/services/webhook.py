"""Webhook admin business logic."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.core.redis_client import get_redis
from app.models.webhook import WebhookLog
from app.schemas.webhook import (
    ReplayResponse,
    TestModeResponse,
    WebhookLogItem,
    WebhookLogListResponse,
)
from app.tasks.webhooks import process_webhook_task

_DEFAULT_PAGE_SIZE = 50


async def list_webhook_logs(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    provider: str | None = None,
    processed: bool | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    cursor: str | None = None,
    limit: int = _DEFAULT_PAGE_SIZE,
) -> WebhookLogListResponse:
    query = select(WebhookLog).where(WebhookLog.tenant_id == tenant_id)

    if provider:
        query = query.where(WebhookLog.provider == provider)
    if processed is not None:
        query = query.where(WebhookLog.processed == processed)
    if date_from:
        query = query.where(WebhookLog.received_at >= date_from)
    if date_to:
        query = query.where(WebhookLog.received_at <= date_to)

    # Cursor-based pagination: cursor = "timestamp:id"
    if cursor:
        try:
            parts = cursor.split(":")
            cursor_ts = float(parts[0])
            cursor_id = uuid.UUID(parts[1])
            cursor_dt = datetime.fromtimestamp(cursor_ts, tz=timezone.utc)
            query = query.where(
                (WebhookLog.received_at < cursor_dt)
                | (
                    (WebhookLog.received_at == cursor_dt)
                    & (WebhookLog.id < cursor_id)
                )
            )
        except Exception:
            raise AppError(ErrorCode.INVALID_CURSOR)

    query = query.order_by(
        WebhookLog.received_at.desc(), WebhookLog.id.desc()
    ).limit(limit + 1)
    result = await db.execute(query)
    rows = list(result.scalars().all())

    has_more = len(rows) > limit
    items = rows[:limit]
    next_cursor: str | None = None
    if has_more and items:
        last = items[-1]
        ts = last.received_at.timestamp() if last.received_at else 0
        next_cursor = f"{ts}:{last.id}"

    return WebhookLogListResponse(
        items=[
            WebhookLogItem(
                id=str(item.id),
                provider=item.provider,
                event_type=item.event_type,
                signature_valid=item.signature_valid,
                processed=item.processed,
                attempts=item.attempts,
                error_message=item.error_message,
                received_at=item.received_at.isoformat() if item.received_at else None,
            )
            for item in items
        ],
        next_cursor=next_cursor,
    )


async def replay_webhook(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    log_id: uuid.UUID,
) -> ReplayResponse:
    log = await db.get(WebhookLog, log_id)
    if not log or log.tenant_id != tenant_id:
        raise AppError(ErrorCode.WEBHOOK_LOG_NOT_FOUND)

    # Increment attempts before dispatch
    log.attempts = (log.attempts or 0) + 1
    await db.commit()

    # Re-dispatch task with stored payload
    process_webhook_task.delay(
        str(log.id),
        str(tenant_id),
        log.provider,
        log.event_type,
        None,  # product_id is not stored separately; resolver uses gateway_ids
        None,
        None,
        "active",  # Default to active on replay; task can infer from event_type
        log.payload or {},
    )

    return ReplayResponse(status="dispatched")


async def set_test_mode(
    tenant_id: uuid.UUID,
    duration_seconds: int,
) -> TestModeResponse:
    redis = get_redis()
    if redis:
        await redis.setex(
            f"webhook:test_mode:{tenant_id}", duration_seconds, "1"
        )
    return TestModeResponse(
        status="test_mode_enabled",
        duration_seconds=duration_seconds,
    )
