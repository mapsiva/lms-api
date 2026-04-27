"""Notifications REST router."""
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, get_current_user, require_admin
from app.models.notification import Notification
from app.models.push_subscription import PushSubscription
from app.models.tenant import Tenant
from app.models.user import User
from app.tasks.notification import dispatch_broadcast_notification_task

router = APIRouter(tags=["notifications"])


# ── Response schemas ──────────────────────────────────────────────────────────


class NotificationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    type: str
    title: str
    body: str | None
    is_read: bool
    created_at: Any


class NotificationListResponse(BaseModel):
    items: list[NotificationItem]
    total: int
    page: int
    page_size: int


class BroadcastRequest(BaseModel):
    type: str | None = "broadcast"
    title: str
    body: str | None = None
    data: dict[str, Any] | None = None


class PushSubscribeRequest(BaseModel):
    endpoint: str
    p256dh: str
    auth: str


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/notifications", response_model=NotificationListResponse)
async def list_notifications(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    offset = (page - 1) * page_size

    total_result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.tenant_id == tenant.id,
            Notification.user_id == user.id,
        )
    )
    total = total_result.scalar() or 0

    result = await db.execute(
        select(Notification)
        .where(
            Notification.tenant_id == tenant.id,
            Notification.user_id == user.id,
        )
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = result.scalars().all()

    return NotificationListResponse(
        items=[NotificationItem.model_validate(n) for n in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(Notification)
        .where(
            Notification.tenant_id == tenant.id,
            Notification.user_id == user.id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    await db.commit()
    return {"status": "ok"}


@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.tenant_id == tenant.id,
            Notification.user_id == user.id,
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.is_read = True
    await db.commit()
    return {"status": "ok"}


# ── Admin broadcast ───────────────────────────────────────────────────────────


@router.post("/admin/notifications/broadcast")
async def broadcast_notification(
    body: BroadcastRequest,
    tenant: Tenant = Depends(get_current_tenant),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a notification for all users in tenant and dispatch via Celery."""
    from sqlalchemy import select

    user_ids_result = await db.execute(
        select(User.id).where(User.tenant_id == tenant.id)
    )
    user_ids = user_ids_result.scalars().all()

    created_ids = []
    for uid in user_ids:
        n = Notification(
            tenant_id=tenant.id,
            user_id=uid,
            type=body.type or "broadcast",
            title=body.title,
            body=body.body,
            data=body.data,
        )
        db.add(n)
        await db.flush()
        created_ids.append(str(n.id))

    await db.commit()

    # Dispatch Celery task for each created notification
    for nid in created_ids:
        dispatch_broadcast_notification_task.delay(
            tenant_id=str(tenant.id),
            notification_id=nid,
            title=body.title,
            body=body.body,
            notification_type=body.type or "broadcast",
        )

    return {"status": "ok", "created_count": len(created_ids)}


# ── Push subscriptions ────────────────────────────────────────────────────────


@router.post("/push/subscribe")
async def subscribe_push(
    body: PushSubscribeRequest,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save a Web Push subscription for the current user."""
    result = await db.execute(
        select(PushSubscription).where(
            PushSubscription.tenant_id == tenant.id,
            PushSubscription.user_id == user.id,
            PushSubscription.endpoint == body.endpoint,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.p256dh = body.p256dh
        existing.auth = body.auth
    else:
        sub = PushSubscription(
            tenant_id=tenant.id,
            user_id=user.id,
            endpoint=body.endpoint,
            p256dh=body.p256dh,
            auth=body.auth,
        )
        db.add(sub)

    await db.commit()
    return {"status": "ok"}


@router.delete("/push/subscribe")
async def unsubscribe_push(
    body: PushSubscribeRequest,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a Web Push subscription for the current user."""
    result = await db.execute(
        select(PushSubscription).where(
            PushSubscription.tenant_id == tenant.id,
            PushSubscription.user_id == user.id,
            PushSubscription.endpoint == body.endpoint,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        await db.delete(existing)
        await db.commit()
    return {"status": "ok"}
