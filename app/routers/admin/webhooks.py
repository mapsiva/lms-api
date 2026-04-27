import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, require_admin
from app.core.redis_client import get_redis
from app.models.tenant import Tenant
from app.models.user import User
from app.models.webhook import WebhookLog
from app.tasks.webhooks import process_webhook_task

router = APIRouter(prefix="/admin/webhooks", tags=["admin:webhooks"])

_DEFAULT_PAGE_SIZE = 50


@router.get("/logs")
async def list_webhook_logs(
    provider: str | None = Query(None),
    processed: bool | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    cursor: str | None = Query(None),
    limit: int = Query(_DEFAULT_PAGE_SIZE, ge=1, le=200),
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(WebhookLog).where(WebhookLog.tenant_id == tenant.id)

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
            raise HTTPException(status_code=400, detail="Invalid cursor")

    query = query.order_by(WebhookLog.received_at.desc(), WebhookLog.id.desc()).limit(
        limit + 1
    )
    result = await db.execute(query)
    rows = list(result.scalars().all())

    has_more = len(rows) > limit
    items = rows[:limit]
    next_cursor = None
    if has_more and items:
        last = items[-1]
        ts = last.received_at.timestamp() if last.received_at else 0
        next_cursor = f"{ts}:{last.id}"

    return {
        "items": [
            {
                "id": str(item.id),
                "provider": item.provider,
                "event_type": item.event_type,
                "signature_valid": item.signature_valid,
                "processed": item.processed,
                "attempts": item.attempts,
                "error_message": item.error_message,
                "received_at": item.received_at.isoformat() if item.received_at else None,
            }
            for item in items
        ],
        "next_cursor": next_cursor,
    }


@router.post("/{log_id}/replay")
async def replay_webhook(
    log_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WebhookLog).where(
            WebhookLog.id == log_id,
            WebhookLog.tenant_id == tenant.id,
        )
    )
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Webhook log not found")

    # Increment attempts before dispatch
    log.attempts = (log.attempts or 0) + 1
    await db.commit()

    # Re-dispatch task with stored payload
    process_webhook_task.delay(
        str(log.id),
        str(tenant.id),
        log.provider,
        log.event_type,
        None,  # product_id is not stored separately; resolver uses gateway_ids
        None,
        None,
        "active",  # Default to active on replay; task can infer from event_type
        log.payload or {},
    )

    return {"status": "dispatched"}


@router.post("/test")
async def set_test_mode(
    duration_seconds: int = Query(300, ge=1, le=3600),
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
):
    redis = get_redis()
    if redis:
        await redis.setex(
            f"webhook:test_mode:{tenant.id}", duration_seconds, "1"
        )
    return {"status": "test_mode_enabled", "duration_seconds": duration_seconds}
