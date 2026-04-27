import datetime
import uuid

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.models.company import Company
from app.models.gamification import Badge, UserBadge, UserLevel, UserStreak, XPEvent
from app.models.user import User
from app.schemas.gamification import (
    BadgeListItem,
    LeaderboardEntry,
    MyStatsResponse,
    TopBadge,
)


async def get_leaderboard(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    company_id: uuid.UUID,
    period: str,
) -> list[LeaderboardEntry]:
    # Validate company belongs to tenant
    company = await db.get(Company, company_id)
    if company is None or company.tenant_id != tenant_id:
        raise AppError(ErrorCode.COMPANY_NOT_FOUND)

    now = datetime.datetime.now(datetime.timezone.utc)
    if period == "week":
        start = now - datetime.timedelta(days=7)
    elif period == "month":
        start = now - datetime.timedelta(days=30)
    else:
        start = None

    stmt = (
        select(UserLevel.user_id, UserLevel.total_xp, func.count(UserBadge.id).label("badges"))
        .join(User, User.id == UserLevel.user_id)
        .outerjoin(UserBadge, UserBadge.user_id == UserLevel.user_id)
        .where(
            UserLevel.tenant_id == tenant_id,
            User.company_id == company_id,
        )
        .group_by(UserLevel.user_id, UserLevel.total_xp)
        .order_by(UserLevel.total_xp.desc())
        .limit(50)
    )

    if start:
        stmt = stmt.where(XPEvent.created_at >= start)

    result = await db.execute(stmt)
    rows = result.all()

    # Fetch names
    users = {row.user_id: row for row in rows}
    names_result = await db.execute(
        select(User.id, User.name).where(User.id.in_(users.keys()))
    )
    names = {uid: name for uid, name in names_result.all()}

    return [
        LeaderboardEntry(
            rank=i + 1,
            user_id=str(row.user_id),
            name=names.get(row.user_id, ""),
            total_xp=row.total_xp,
            badges=row.badges,
        )
        for i, row in enumerate(rows)
    ]


async def get_my_stats(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> MyStatsResponse:
    result = await db.execute(
        select(UserLevel).where(
            UserLevel.tenant_id == tenant_id,
            UserLevel.user_id == user_id,
        )
    )
    level = result.scalar_one_or_none()

    streak_result = await db.execute(
        select(UserStreak).where(UserStreak.user_id == user_id)
    )
    streak = streak_result.scalar_one_or_none()

    # Top 3 rarest badges
    badges_result = await db.execute(
        select(Badge, UserBadge.awarded_at)
        .join(UserBadge, UserBadge.badge_id == Badge.id)
        .where(UserBadge.user_id == user_id)
        .order_by(
            case(
                (Badge.rarity == "legendary", 1),
                (Badge.rarity == "epic", 2),
                (Badge.rarity == "rare", 3),
                (Badge.rarity == "common", 4),
                else_=5,
            )
        )
        .limit(3)
    )
    top_badges = [
        TopBadge(
            id=str(b.id),
            name=b.name,
            rarity=b.rarity,
            awarded_at=str(at),
        )
        for b, at in badges_result.all()
    ]

    return MyStatsResponse(
        total_xp=level.total_xp if level else 0,
        level=level.level if level else 1,
        current_streak=streak.current_streak if streak else 0,
        longest_streak=streak.longest_streak if streak else 0,
        top_badges=top_badges,
    )


async def list_badges(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list[BadgeListItem]:
    result = await db.execute(
        select(Badge).where(Badge.tenant_id == tenant_id, Badge.is_active == True)  # noqa: E712
    )
    badges = result.scalars().all()

    # User's earned badges
    earned_result = await db.execute(
        select(UserBadge.badge_id).where(UserBadge.user_id == user_id)
    )
    earned = {str(b) for b in earned_result.scalars().all()}

    return [
        BadgeListItem(
            id=str(b.id),
            name=b.name,
            category=b.category,
            rarity=b.rarity,
            earned=str(b.id) in earned,
        )
        for b in badges
    ]
