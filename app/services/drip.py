from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Lesson
from app.models.enrollment import Enrollment
from app.models.progress import LessonProgress


@dataclass
class DripResult:
    accessible: bool
    reason: str
    unlocks_at: Optional[datetime] = None


async def is_lesson_accessible(
    db: AsyncSession,
    user_id,
    lesson: Lesson,
    enrollment: Enrollment,
) -> DripResult:
    if lesson.drip_type == "immediate":
        return DripResult(accessible=True, reason="immediate access")

    now = datetime.now(timezone.utc)

    if lesson.drip_type == "fixed_date":
        drip_value = lesson.drip_value or {}
        date_str = drip_value.get("date")
        if not date_str:
            return DripResult(accessible=True, reason="no date configured")
        unlock_date = datetime.fromisoformat(date_str)
        if unlock_date.tzinfo is None:
            unlock_date = unlock_date.replace(tzinfo=timezone.utc)
        if now >= unlock_date:
            return DripResult(accessible=True, reason="past unlock date")
        return DripResult(accessible=False, reason=f"unlocks on {date_str}", unlocks_at=unlock_date)

    if lesson.drip_type == "days_after_enrollment":
        drip_value = lesson.drip_value or {}
        days = int(drip_value.get("days", 0))
        enrolled_at = enrollment.created_at
        if enrolled_at.tzinfo is None:
            enrolled_at = enrolled_at.replace(tzinfo=timezone.utc)
        unlocks_at = enrolled_at + timedelta(days=days)
        if now >= unlocks_at:
            return DripResult(accessible=True, reason="days elapsed")
        return DripResult(
            accessible=False,
            reason=f"unlocks {days} days after enrollment",
            unlocks_at=unlocks_at,
        )

    if lesson.drip_type == "prerequisite":
        drip_value = lesson.drip_value or {}
        prereq_id = drip_value.get("lesson_id")
        if not prereq_id:
            return DripResult(accessible=True, reason="no prerequisite configured")
        import uuid
        result = await db.execute(
            select(LessonProgress).where(
                LessonProgress.user_id == user_id,
                LessonProgress.lesson_id == uuid.UUID(str(prereq_id)),
                LessonProgress.completed_at.isnot(None),
            )
        )
        if result.scalar_one_or_none() is not None:
            return DripResult(accessible=True, reason="prerequisite completed")
        return DripResult(accessible=False, reason="prerequisite lesson not completed")

    return DripResult(accessible=True, reason="unknown drip type — defaulting to accessible")
