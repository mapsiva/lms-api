"""XP award service."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gamification import SpecialEvent, UserLevel, XPEvent

# Default XP amounts per action (overridden by tenant.features if present)
_DEFAULT_XP = {
    "lesson_completed": 10,
    "quiz_passed": 20,
    "comment_posted": 5,
    "post_liked": 2,
    "streak_maintained": 15,
    "badge_earned": 25,
    "battle_won": 30,
    "battle_participated": 10,
}

# Default level thresholds (XP needed for each level)
_DEFAULT_THRESHOLDS = [0, 100, 300, 600, 1000, 1500, 2100, 2800, 3600, 4500]


async def _get_xp_for_action(session: AsyncSession, tenant_id: uuid.UUID, action: str) -> int:
    from app.models.tenant import Tenant

    tenant = await session.get(Tenant, tenant_id)
    features = tenant.features if tenant and tenant.features else {}
    xp_map = features.get("xp_amounts", {})
    return xp_map.get(action, _DEFAULT_XP.get(action, 0))


async def _get_level_thresholds(session: AsyncSession, tenant_id: uuid.UUID) -> list[int]:
    from app.models.tenant import Tenant

    tenant = await session.get(Tenant, tenant_id)
    features = tenant.features if tenant and tenant.features else {}
    return features.get("level_thresholds", _DEFAULT_THRESHOLDS)


async def _compute_level(total_xp: int, thresholds: list[int]) -> int:
    level = 1
    for i, threshold in enumerate(thresholds):
        if total_xp >= threshold:
            level = i + 1
        else:
            break
    return max(level, 1)


async def _active_multiplier(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    company_id: uuid.UUID | None,
) -> int:
    now = datetime.now(timezone.utc)
    stmt = (
        select(SpecialEvent)
        .where(SpecialEvent.tenant_id == tenant_id)
        .where(SpecialEvent.is_active == True)  # noqa: E712
        .where(SpecialEvent.starts_at <= now)
        .where(SpecialEvent.ends_at >= now)
    )
    if company_id:
        stmt = stmt.where(
            (SpecialEvent.company_id == company_id) | (SpecialEvent.company_id.is_(None))
        )
    else:
        stmt = stmt.where(SpecialEvent.company_id.is_(None))

    result = await session.execute(stmt.limit(1))
    event = result.scalar_one_or_none()
    if event and event.xp_multiplier:
        return event.xp_multiplier
    return 1


async def award_xp(
    session: AsyncSession,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    company_id: uuid.UUID | None,
    action: str,
    reference_id: uuid.UUID | None = None,
    reference_type: str | None = None,
) -> dict:
    """Create XP event, update user level, return {event_id, leveled_up, old_level, new_level}."""
    amount = await _get_xp_for_action(session, tenant_id, action)
    multiplier = await _active_multiplier(session, tenant_id, company_id)
    final_amount = amount * multiplier

    # Append-only XP event
    event = XPEvent(
        tenant_id=tenant_id,
        user_id=user_id,
        company_id=company_id,
        action=action,
        amount=final_amount,
        reference_id=reference_id,
        reference_type=reference_type,
    )
    session.add(event)

    # Update or create UserLevel
    result = await session.execute(
        select(UserLevel).where(
            UserLevel.tenant_id == tenant_id,
            UserLevel.user_id == user_id,
        )
    )
    user_level = result.scalar_one_or_none()
    if user_level is None:
        user_level = UserLevel(tenant_id=tenant_id, user_id=user_id, total_xp=0, level=1)
        session.add(user_level)
        await session.flush()

    old_level = user_level.level
    old_total = user_level.total_xp
    user_level.total_xp = old_total + final_amount

    thresholds = await _get_level_thresholds(session, tenant_id)
    new_level = await _compute_level(user_level.total_xp, thresholds)
    user_level.level = new_level

    await session.commit()

    return {
        "event_id": event.id,
        "leveled_up": new_level > old_level,
        "old_level": old_level,
        "new_level": new_level,
        "xp_awarded": final_amount,
    }
