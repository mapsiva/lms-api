"""Unit tests for XP award service."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.gamification import SpecialEvent, UserLevel, XPEvent
from app.services.gamification.xp import (
    _active_multiplier,
    _compute_level,
    _get_level_thresholds,
    _get_xp_for_action,
    award_xp,
)


@pytest.mark.asyncio
async def test_get_xp_default(db_session, tenant):
    amount = await _get_xp_for_action(db_session, tenant.id, "lesson_completed")
    assert amount == 10


@pytest.mark.asyncio
async def test_get_xp_from_tenant_features(db_session, tenant):
    tenant.features = {"xp_amounts": {"lesson_completed": 50}}
    await db_session.commit()
    amount = await _get_xp_for_action(db_session, tenant.id, "lesson_completed")
    assert amount == 50


@pytest.mark.asyncio
async def test_compute_level(db_session):
    assert await _compute_level(0, [0, 100, 300]) == 1
    assert await _compute_level(100, [0, 100, 300]) == 2
    assert await _compute_level(300, [0, 100, 300]) == 3
    assert await _compute_level(500, [0, 100, 300]) == 3


@pytest.mark.asyncio
async def test_active_multiplier_no_event(db_session, tenant):
    m = await _active_multiplier(db_session, tenant.id, None)
    assert m == 1


@pytest.mark.asyncio
async def test_active_multiplier_with_event(db_session, tenant):
    now = datetime.now(timezone.utc)
    ev = SpecialEvent(
        tenant_id=tenant.id,
        name="Double XP",
        event_type="double_xp",
        xp_multiplier=2,
        starts_at=now - timedelta(minutes=1),
        ends_at=now + timedelta(hours=1),
        is_active=True,
    )
    db_session.add(ev)
    await db_session.commit()

    m = await _active_multiplier(db_session, tenant.id, None)
    assert m == 2


@pytest.mark.asyncio
async def test_award_xp_creates_event_and_level(db_session, tenant, user):
    result = await award_xp(db_session, user.id, tenant.id, None, "lesson_completed")
    assert result["xp_awarded"] == 10
    assert result["leveled_up"] is False
    assert result["old_level"] == 1
    assert result["new_level"] == 1

    event = await db_session.execute(select(XPEvent).where(XPEvent.user_id == user.id))
    assert event.scalar_one_or_none() is not None

    level = await db_session.execute(select(UserLevel).where(UserLevel.user_id == user.id))
    ul = level.scalar_one_or_none()
    assert ul is not None
    assert ul.total_xp == 10


@pytest.mark.asyncio
async def test_award_xp_level_up(db_session, tenant, user):
    # Award enough XP to cross level 2 threshold (100 XP); battle_won = 30 XP each
    for _ in range(4):
        result = await award_xp(db_session, user.id, tenant.id, None, "battle_won")
    assert result["new_level"] >= 2
