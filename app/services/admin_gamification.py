"""Admin service for badge and special event management."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.models.gamification import Badge, SpecialEvent
from app.schemas.gamification import (
    BadgeAdminResponse,
    BadgeCreate,
    BadgeUpdate,
    SpecialEventCreate,
    SpecialEventResponse,
)


async def list_badges(db: AsyncSession, tenant_id: uuid.UUID) -> list[BadgeAdminResponse]:
    result = await db.execute(
        select(Badge).where(Badge.tenant_id == tenant_id).order_by(Badge.created_at.desc())
    )
    return [BadgeAdminResponse.model_validate(b) for b in result.scalars().all()]


async def create_badge(
    db: AsyncSession, tenant_id: uuid.UUID, data: BadgeCreate
) -> BadgeAdminResponse:
    badge = Badge(tenant_id=tenant_id, **data.model_dump())
    db.add(badge)
    await db.commit()
    await db.refresh(badge)
    return BadgeAdminResponse.model_validate(badge)


async def update_badge(
    db: AsyncSession, tenant_id: uuid.UUID, badge_id: uuid.UUID, data: BadgeUpdate
) -> BadgeAdminResponse:
    badge = await db.get(Badge, badge_id)
    if badge is None or badge.tenant_id != tenant_id:
        raise AppError(ErrorCode.BADGE_NOT_FOUND)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(badge, field, value)
    await db.commit()
    await db.refresh(badge)
    return BadgeAdminResponse.model_validate(badge)


async def delete_badge(
    db: AsyncSession, tenant_id: uuid.UUID, badge_id: uuid.UUID
) -> None:
    badge = await db.get(Badge, badge_id)
    if badge is None or badge.tenant_id != tenant_id:
        raise AppError(ErrorCode.BADGE_NOT_FOUND)
    await db.delete(badge)
    await db.commit()


async def list_special_events(
    db: AsyncSession, tenant_id: uuid.UUID
) -> list[SpecialEventResponse]:
    result = await db.execute(
        select(SpecialEvent)
        .where(SpecialEvent.tenant_id == tenant_id)
        .order_by(SpecialEvent.starts_at.desc())
    )
    return [SpecialEventResponse.model_validate(e) for e in result.scalars().all()]


async def create_special_event(
    db: AsyncSession, tenant_id: uuid.UUID, data: SpecialEventCreate
) -> SpecialEventResponse:
    event = SpecialEvent(tenant_id=tenant_id, **data.model_dump())
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return SpecialEventResponse.model_validate(event)


async def delete_special_event(
    db: AsyncSession, tenant_id: uuid.UUID, event_id: uuid.UUID
) -> None:
    event = await db.get(SpecialEvent, event_id)
    if event is None or event.tenant_id != tenant_id:
        raise AppError(ErrorCode.SPECIAL_EVENT_NOT_FOUND)
    await db.delete(event)
    await db.commit()
