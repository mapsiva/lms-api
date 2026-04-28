"""Unit tests for badge evaluation service."""
import pytest
from sqlalchemy import select

from app.models.gamification import Badge, UserBadge, UserStreak, XPEvent
from app.services.gamification.badges import evaluate_badges


@pytest.mark.asyncio
async def test_evaluate_badges_no_match(db_session, tenant, user):
    awarded = await evaluate_badges(db_session, user.id, tenant.id, "lesson_completed")
    assert awarded == []


@pytest.mark.asyncio
async def test_evaluate_badges_min_xp(db_session, tenant, user):
    badge = Badge(
        tenant_id=tenant.id,
        name="XP Master",
        category="completion",
        rarity="common",
        is_active=True,
        rule_event="lesson_completed",
        rule_conditions={"min_xp": 50},
    )
    db_session.add(badge)
    await db_session.commit()

    # No XP yet — should not award
    awarded = await evaluate_badges(db_session, user.id, tenant.id, "lesson_completed")
    assert awarded == []

    # Add XP
    xp = XPEvent(tenant_id=tenant.id, user_id=user.id, action="lesson_completed", amount=100)
    db_session.add(xp)
    await db_session.commit()

    awarded = await evaluate_badges(db_session, user.id, tenant.id, "lesson_completed")
    assert len(awarded) == 1
    assert awarded[0] == badge.id

    # Should not award twice
    awarded = await evaluate_badges(db_session, user.id, tenant.id, "lesson_completed")
    assert awarded == []


@pytest.mark.asyncio
async def test_evaluate_badges_streak_days(db_session, tenant, user):
    streak = UserStreak(user_id=user.id, current_streak=7, longest_streak=7)
    db_session.add(streak)

    badge = Badge(
        tenant_id=tenant.id,
        name="Week Streak",
        category="behavior",
        rarity="rare",
        is_active=True,
        rule_event="streak_maintained",
        rule_conditions={"streak_days": 7},
    )
    db_session.add(badge)
    await db_session.commit()

    awarded = await evaluate_badges(db_session, user.id, tenant.id, "streak_maintained")
    assert len(awarded) == 1
