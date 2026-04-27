"""Gamification router."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, get_current_user
from app.models.gamification import (
    Badge,
    UserBadge,
    UserLevel,
    UserStreak,
    XPEvent,
)
from app.models.user import User

router = APIRouter(prefix="/gamification", tags=["gamification"])


@router.get("/leaderboard")
async def leaderboard(
    company_id: uuid.UUID,
    period: str = Query("all", enum=["week", "month", "all"]),
    tenant=Depends(get_current_tenant),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validate company belongs to tenant
    from app.models.company import Company

    company = await db.get(Company, company_id)
    if company is None or company.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Company not found")

    import datetime

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
            UserLevel.tenant_id == tenant.id,
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
    names_result = await db.execute(select(User.id, User.name).where(User.id.in_(users.keys())))
    names = {uid: name for uid, name in names_result.all()}

    return [
        {
            "rank": i + 1,
            "user_id": str(row.user_id),
            "name": names.get(row.user_id, ""),
            "total_xp": row.total_xp,
            "badges": row.badges,
        }
        for i, row in enumerate(rows)
    ]


@router.get("/my-stats")
async def my_stats(
    user: User = Depends(get_current_user),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserLevel).where(
            UserLevel.tenant_id == tenant.id,
            UserLevel.user_id == user.id,
        )
    )
    level = result.scalar_one_or_none()

    streak_result = await db.execute(
        select(UserStreak).where(UserStreak.user_id == user.id)
    )
    streak = streak_result.scalar_one_or_none()

    # Top 3 rarest badges
    badges_result = await db.execute(
        select(Badge, UserBadge.awarded_at)
        .join(UserBadge, UserBadge.badge_id == Badge.id)
        .where(UserBadge.user_id == user.id)
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
        {"id": str(b.id), "name": b.name, "rarity": b.rarity, "awarded_at": str(at)}
        for b, at in badges_result.all()
    ]

    return {
        "total_xp": level.total_xp if level else 0,
        "level": level.level if level else 1,
        "current_streak": streak.current_streak if streak else 0,
        "longest_streak": streak.longest_streak if streak else 0,
        "top_badges": top_badges,
    }


@router.get("/badges")
async def list_badges(
    tenant=Depends(get_current_tenant),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Badge).where(Badge.tenant_id == tenant.id, Badge.is_active == True)  # noqa: E712
    )
    badges = result.scalars().all()

    # User's earned badges
    earned_result = await db.execute(
        select(UserBadge.badge_id).where(UserBadge.user_id == _user.id)
    )
    earned = {str(b) for b in earned_result.scalars().all()}

    return [
        {
            "id": str(b.id),
            "name": b.name,
            "category": b.category,
            "rarity": b.rarity,
            "earned": str(b.id) in earned,
        }
        for b in badges
    ]
