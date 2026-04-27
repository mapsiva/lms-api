import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import get_db
from app.core.dependencies import get_current_tenant
from app.core.redis_client import get_redis
from app.integrations.webhooks.base import WebhookEvent
from app.integrations.webhooks.hotmart import parse_hotmart_webhook
from app.integrations.webhooks.kiwify import parse_kiwify_webhook
from app.integrations.webhooks.greenn import parse_greenn_webhook
from app.integrations.webhooks.monetizze import parse_monetizze_webhook
from app.integrations.webhooks.stripe import parse_stripe_webhook
from app.models.tenant import Tenant
from app.models.webhook import WebhookLog
from app.tasks.webhooks import process_webhook_task

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


_PARSERS = {
    "hotmart": parse_hotmart_webhook,
    "kiwify": parse_kiwify_webhook,
    "greenn": parse_greenn_webhook,
    "monetizze": parse_monetizze_webhook,
    "stripe": parse_stripe_webhook,
}

_SECRET_KEYS = {
    "hotmart": "hotmart_webhook_secret",
    "kiwify": "kiwify_webhook_secret",
    "greenn": "greenn_webhook_secret",
    "monetizze": "monetizze_webhook_secret",
    "stripe": "stripe_webhook_secret",
}


async def _log_webhook(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    provider: str,
    event_type: str,
    payload: dict[str, Any] | None,
    signature_valid: bool,
    error_message: str | None = None,
) -> WebhookLog:
    log = WebhookLog(
        tenant_id=tenant_id,
        provider=provider,
        event_type=event_type,
        payload=payload,
        signature_valid=signature_valid,
        error_message=error_message,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


@router.post("/{provider}", status_code=200)
async def receive_webhook(
    request: Request,
    provider: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    raw_body = await request.body()
    headers = dict(request.headers)

    parser = _PARSERS.get(provider)
    if not parser:
        return JSONResponse(content={"status": "ok"}, status_code=200)

    secret_key = _SECRET_KEYS.get(provider)
    secret = (
        getattr(settings, secret_key).get_secret_value()
        if secret_key and getattr(settings, secret_key)
        else ""
    )

    event: WebhookEvent | None = None
    signature_valid = False
    try:
        event, signature_valid = parser(raw_body, headers, secret)
    except Exception as e:
        await _log_webhook(
            db,
            tenant.id,
            provider,
            "ERROR",
            None,
            False,
            str(e),
        )
        return JSONResponse(content={"status": "ok"}, status_code=200)

    event_type = event.event_type if event else "UNKNOWN"
    payload = event.raw_payload if event else None

    log = await _log_webhook(
        db,
        tenant.id,
        provider,
        event_type,
        payload,
        signature_valid,
        None,
    )

    if signature_valid and event and event.status:
        redis = get_redis()
        test_mode = False
        if redis:
            test_mode = await redis.get(f"webhook:test_mode:{tenant.id}")
        if test_mode:
            # Skip dispatch in test mode
            pass
        else:
            process_webhook_task.delay(
                str(log.id),
                str(tenant.id),
                event.provider,
                event.event_type,
                event.product_id,
                event.buyer_email,
                event.buyer_name,
                event.status,
                event.raw_payload,
            )

    return JSONResponse(content={"status": "ok"}, status_code=200)
