"""Unit tests for gamification Celery task logic via service layer.

Tasks use asyncio.run() internally which can't be called within a running
event loop (pytest-asyncio). Tests exercise the underlying service functions
directly — the tasks are thin wrappers around the same logic.
"""
import pytest
from sqlalchemy import select

from app.models.gamification import UserLevel, UserStreak, XPEvent
from app.services.gamification.badges import evaluate_badges
from app.services.gamification.streaks import update_streak
from app.services.gamification.xp import award_xp


@pytest.mark.asyncio
async def test_award_xp_creates_event_and_level(db_session, tenant, user):
    result = await award_xp(db_session, user.id, tenant.id, None, "lesson_completed")
    assert result["xp_awarded"] == 10
    assert "leveled_up" in result

    xp = await db_session.execute(select(XPEvent).where(XPEvent.user_id == user.id))
    assert xp.scalar_one_or_none() is not None

    level = await db_session.execute(select(UserLevel).where(UserLevel.user_id == user.id))
    ul = level.scalar_one_or_none()
    assert ul is not None
    assert ul.total_xp == 10


@pytest.mark.asyncio
async def test_evaluate_badges_no_badges(db_session, tenant, user):
    awarded = await evaluate_badges(db_session, user.id, tenant.id, "lesson_completed")
    assert awarded == []


@pytest.mark.asyncio
async def test_update_streak_via_service(db_session, user):
    result = await update_streak(db_session, user.id, None)
    assert result["current"] == 1
    assert result["reset"] is False

    streak = await db_session.execute(select(UserStreak).where(UserStreak.user_id == user.id))
    assert streak.scalar_one_or_none() is not None
