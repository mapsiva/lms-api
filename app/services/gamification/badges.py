"""Badge evaluation service."""
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gamification import Badge, UserBadge, XPEvent
from app.models.progress import LessonProgress


async def _count_xp(session: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID) -> int:
    result = await session.execute(
        select(func.sum(XPEvent.amount))
        .where(XPEvent.user_id == user_id, XPEvent.tenant_id == tenant_id)
    )
    return result.scalar() or 0


async def _count_completed_courses(session: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID) -> int:
    from app.models.course import Course, Lesson, Module
    from sqlalchemy import distinct

    result = await session.execute(
        select(func.count(distinct(Course.id)))
        .select_from(LessonProgress)
        .join(Lesson, Lesson.id == LessonProgress.lesson_id)
        .join(Module, Module.id == Lesson.module_id)
        .join(Course, Course.id == Module.course_id)
        .where(
            LessonProgress.user_id == user_id,
            Course.tenant_id == tenant_id,
            LessonProgress.completed_at.isnot(None),
        )
    )
    return result.scalar() or 0


async def _count_streak_days(session: AsyncSession, user_id: uuid.UUID) -> int:
    from app.models.gamification import UserStreak

    result = await session.execute(select(UserStreak).where(UserStreak.user_id == user_id))
    streak = result.scalar_one_or_none()
    if streak:
        return streak.current_streak
    return 0


async def _count_comments(session: AsyncSession, user_id: uuid.UUID) -> int:
    from app.models.community import Comment

    result = await session.execute(
        select(func.count(Comment.id)).where(Comment.user_id == user_id)
    )
    return result.scalar() or 0


async def evaluate_badges(
    session: AsyncSession,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    trigger_event: str,
) -> list[uuid.UUID]:
    """Evaluate and award badges matching trigger_event. Returns list of newly awarded badge IDs."""
    result = await session.execute(
        select(Badge)
        .where(Badge.tenant_id == tenant_id)
        .where(Badge.is_active == True)  # noqa: E712
        .where(Badge.rule_event == trigger_event)
    )
    badges = result.scalars().all()

    awarded = []
    for badge in badges:
        # Skip already awarded
        existing = await session.execute(
            select(UserBadge).where(
                UserBadge.user_id == user_id,
                UserBadge.badge_id == badge.id,
            )
        )
        if existing.scalar_one_or_none():
            continue

        conditions = badge.rule_conditions or {}
        met = await _check_conditions(session, user_id, tenant_id, conditions)
        if met:
            ub = UserBadge(user_id=user_id, badge_id=badge.id)
            session.add(ub)
            awarded.append(badge.id)

    if awarded:
        await session.commit()

    return awarded


async def _check_conditions(
    session: AsyncSession,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    conditions: dict,
) -> bool:
    if "min_xp" in conditions:
        xp = await _count_xp(session, user_id, tenant_id)
        if xp < conditions["min_xp"]:
            return False

    if "courses_completed" in conditions:
        count = await _count_completed_courses(session, user_id, tenant_id)
        if count < conditions["courses_completed"]:
            return False

    if "streak_days" in conditions:
        days = await _count_streak_days(session, user_id)
        if days < conditions["streak_days"]:
            return False

    if "hour_before" in conditions:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        if now.hour >= conditions["hour_before"]:
            return False

    if "answers_given" in conditions:
        count = await _count_comments(session, user_id)
        if count < conditions["answers_given"]:
            return False

    return True
