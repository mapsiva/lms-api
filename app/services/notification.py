"""Business logic for notifications."""
import uuid
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.models.notification import Notification
from app.models.push_subscription import PushSubscription
from app.models.user import User
from app.schemas.notification import BroadcastRequest, NotificationItem, NotificationListResponse
from app.tasks.notification import dispatch_broadcast_notification_task


async def list_notifications(
    db: AsyncSession, tenant_id: Any, user_id: Any, page: int, page_size: int
) -> NotificationListResponse:
    offset = (page - 1) * page_size

    total_result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.tenant_id == tenant_id,
            Notification.user_id == user_id,
        )
    )
    total = total_result.scalar() or 0

    result = await db.execute(
        select(Notification)
        .where(
            Notification.tenant_id == tenant_id,
            Notification.user_id == user_id,
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


async def mark_all_read(db: AsyncSession, tenant_id: Any, user_id: Any) -> None:
    await db.execute(
        update(Notification)
        .where(
            Notification.tenant_id == tenant_id,
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    await db.commit()


async def mark_notification_read(
    db: AsyncSession, tenant_id: Any, user_id: Any, notification_id: uuid.UUID
) -> None:
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.tenant_id == tenant_id,
            Notification.user_id == user_id,
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise AppError(ErrorCode.NOTIFICATION_NOT_FOUND)

    notification.is_read = True
    await db.commit()


async def broadcast_notification(
    db: AsyncSession, tenant_id: Any, body: BroadcastRequest
) -> int:
    user_ids_result = await db.execute(
        select(User.id).where(User.tenant_id == tenant_id)
    )
    user_ids = user_ids_result.scalars().all()

    created_ids: list[str] = []
    for uid in user_ids:
        n = Notification(
            tenant_id=tenant_id,
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

    for nid in created_ids:
        dispatch_broadcast_notification_task.delay(
            tenant_id=str(tenant_id),
            notification_id=nid,
            title=body.title,
            body=body.body,
            notification_type=body.type or "broadcast",
        )

    return len(created_ids)


async def subscribe_push(
    db: AsyncSession, tenant_id: Any, user_id: Any, endpoint: str, p256dh: str, auth: str
) -> None:
    result = await db.execute(
        select(PushSubscription).where(
            PushSubscription.tenant_id == tenant_id,
            PushSubscription.user_id == user_id,
            PushSubscription.endpoint == endpoint,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.p256dh = p256dh
        existing.auth = auth
    else:
        sub = PushSubscription(
            tenant_id=tenant_id,
            user_id=user_id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
        )
        db.add(sub)

    await db.commit()


async def unsubscribe_push(
    db: AsyncSession, tenant_id: Any, user_id: Any, endpoint: str
) -> None:
    result = await db.execute(
        select(PushSubscription).where(
            PushSubscription.tenant_id == tenant_id,
            PushSubscription.user_id == user_id,
            PushSubscription.endpoint == endpoint,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        await db.delete(existing)
        await db.commit()
