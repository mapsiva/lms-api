"""Notifications REST router."""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, get_current_user, require_admin
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.notification import (
    BroadcastRequest,
    BroadcastResponse,
    NotificationListResponse,
    PushSubscribeRequest,
    StatusOkResponse,
)
from app.services import notification as notification_service

router = APIRouter(tags=["notifications"])


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/notifications", response_model=NotificationListResponse)
async def list_notifications(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    return await notification_service.list_notifications(
        db, tenant.id, user.id, page, page_size
    )


@router.post("/notifications/read-all", response_model=StatusOkResponse)
async def mark_all_notifications_read(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await notification_service.mark_all_read(db, tenant.id, user.id)
    return StatusOkResponse(status="ok")


@router.patch("/notifications/{notification_id}/read", response_model=StatusOkResponse)
async def mark_notification_read(
    notification_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await notification_service.mark_notification_read(
        db, tenant.id, user.id, notification_id
    )
    return StatusOkResponse(status="ok")


# ── Admin broadcast ───────────────────────────────────────────────────────────


@router.post("/admin/notifications/broadcast", response_model=BroadcastResponse)
async def broadcast_notification(
    body: BroadcastRequest,
    tenant: Tenant = Depends(get_current_tenant),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a notification for all users in tenant and dispatch via Celery."""
    created_count = await notification_service.broadcast_notification(
        db, tenant.id, body
    )
    return BroadcastResponse(status="ok", created_count=created_count)


# ── Push subscriptions ────────────────────────────────────────────────────────


@router.post("/push/subscribe", response_model=StatusOkResponse)
async def subscribe_push(
    body: PushSubscribeRequest,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save a Web Push subscription for the current user."""
    await notification_service.subscribe_push(
        db, tenant.id, user.id, body.endpoint, body.p256dh, body.auth
    )
    return StatusOkResponse(status="ok")


@router.delete("/push/subscribe", response_model=StatusOkResponse)
async def unsubscribe_push(
    body: PushSubscribeRequest,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a Web Push subscription for the current user."""
    await notification_service.unsubscribe_push(db, tenant.id, user.id, body.endpoint)
    return StatusOkResponse(status="ok")
