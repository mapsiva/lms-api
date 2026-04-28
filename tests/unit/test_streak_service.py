"""Unit tests for streak service."""
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select

from app.models.gamification import UserStreak
from app.services.gamification.streaks import update_streak


@pytest.mark.asyncio
async def test_update_streak_new_user(db_session, user):
    result = await update_streak(db_session, user.id, None)
    assert result["current"] == 1
    assert result["longest"] == 1
    assert result["reset"] is False
    assert result["shield_used"] is False

    row = await db_session.execute(select(UserStreak).where(UserStreak.user_id == user.id))
    streak = row.scalar_one_or_none()
    assert streak is not None
    assert streak.current_streak == 1


@pytest.mark.asyncio
async def test_update_streak_same_day(db_session, user):
    today = datetime.now(timezone.utc).date()
    streak = UserStreak(
        user_id=user.id,
        current_streak=5,
        longest_streak=5,
        last_activity_date=today,
    )
    db_session.add(streak)
    await db_session.commit()

    result = await update_streak(db_session, user.id, None)
    assert result["current"] == 5
    assert result["shield_used"] is False


@pytest.mark.asyncio
async def test_update_streak_consecutive_day(db_session, user):
    today = datetime.now(timezone.utc).date()
    streak = UserStreak(
        user_id=user.id,
        current_streak=5,
        longest_streak=5,
        last_activity_date=today - date.resolution,
    )
    db_session.add(streak)
    await db_session.commit()

    result = await update_streak(db_session, user.id, None)
    assert result["current"] == 6
    assert result["shield_used"] is False
    assert result["reset"] is False


@pytest.mark.asyncio
async def test_update_streak_shield_used(db_session, user):
    today = datetime.now(timezone.utc).date()
    streak = UserStreak(
        user_id=user.id,
        current_streak=5,
        longest_streak=5,
        shields_available=1,
        last_activity_date=today - date.resolution - date.resolution,
    )
    db_session.add(streak)
    await db_session.commit()

    result = await update_streak(db_session, user.id, None)
    assert result["current"] == 6
    assert result["shield_used"] is True
    assert result["reset"] is False

    row = await db_session.execute(select(UserStreak).where(UserStreak.user_id == user.id))
    streak = row.scalar_one_or_none()
    assert streak is not None
    assert streak.shields_available == 0


@pytest.mark.asyncio
async def test_update_streak_reset(db_session, user):
    today = datetime.now(timezone.utc).date()
    streak = UserStreak(
        user_id=user.id,
        current_streak=5,
        longest_streak=5,
        shields_available=0,
        last_activity_date=today - date.resolution - date.resolution - date.resolution,
    )
    db_session.add(streak)
    await db_session.commit()

    result = await update_streak(db_session, user.id, None)
    assert result["current"] == 1
    assert result["reset"] is True
