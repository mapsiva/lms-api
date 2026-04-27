"""Admin webhooks router."""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, require_admin
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.webhook import (
    ReplayResponse,
    TestModeResponse,
    WebhookLogListResponse,
)
from app.services import webhook as webhook_service

router = APIRouter(prefix="/admin/webhooks", tags=["admin:webhooks"])

_DEFAULT_PAGE_SIZE = 50


@router.get("/logs", response_model=WebhookLogListResponse)
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
    return await webhook_service.list_webhook_logs(
        db,
        tenant.id,
        provider=provider,
        processed=processed,
        date_from=date_from,
        date_to=date_to,
        cursor=cursor,
        limit=limit,
    )


@router.post("/{log_id}/replay", response_model=ReplayResponse)
async def replay_webhook(
    log_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await webhook_service.replay_webhook(db, tenant.id, log_id)


@router.post("/test", response_model=TestModeResponse)
async def set_test_mode(
    duration_seconds: int = Query(300, ge=1, le=3600),
    tenant: Tenant = Depends(get_current_tenant),
    _admin: User = Depends(require_admin),
):
    return await webhook_service.set_test_mode(tenant.id, duration_seconds)
