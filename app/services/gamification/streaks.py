"""Streak service."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gamification import UserStreak


async def update_streak(
    session: AsyncSession,
    user_id: uuid.UUID,
    company_id: uuid.UUID | None,
) -> dict:
    """Update streak on daily first activity. Returns {current, longest, shield_used, reset}."""
    result = await session.execute(select(UserStreak).where(UserStreak.user_id == user_id))
    streak = result.scalar_one_or_none()
    today = datetime.now(timezone.utc).date()

    if streak is None:
        streak = UserStreak(
            user_id=user_id,
            company_id=company_id,
            current_streak=1,
            longest_streak=1,
            last_activity_date=today,
        )
        session.add(streak)
        await session.commit()
        return {"current": 1, "longest": 1, "shield_used": False, "reset": False}

    last: datetime | None = streak.last_activity_date
    if last == today:
        # Already active today
        return {"current": streak.current_streak, "longest": streak.longest_streak, "shield_used": False, "reset": False}

    gap_days = (today - last).days if last else 2

    shield_used = False
    reset = False

    if gap_days == 1:
        # Consecutive day
        streak.current_streak += 1
    elif gap_days == 2 and streak.shields_available > 0:
        # Shield covers a single gap day
        streak.shields_available -= 1
        streak.current_streak += 1
        shield_used = True
    else:
        # Reset streak
        streak.current_streak = 1
        reset = True

    if streak.current_streak > streak.longest_streak:
        streak.longest_streak = streak.current_streak

    streak.last_activity_date = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
    await session.commit()

    return {
        "current": streak.current_streak,
        "longest": streak.longest_streak,
        "shield_used": shield_used,
        "reset": reset,
    }
