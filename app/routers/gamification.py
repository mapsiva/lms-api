"""Gamification router."""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, get_current_user
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.gamification import (
    BadgeListItem,
    LeaderboardEntry,
    MyStatsResponse,
)
from app.services import gamification as gamification_service
from app.services.hall_of_fame import compute_monthly_hall_of_fame

router = APIRouter(prefix="/gamification", tags=["gamification"])


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
async def leaderboard(
    company_id: uuid.UUID,
    period: str = Query("all", enum=["week", "month", "all"]),
    tenant: Tenant = Depends(get_current_tenant),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await gamification_service.get_leaderboard(db, tenant.id, company_id, period)


@router.get("/my-stats", response_model=MyStatsResponse)
async def my_stats(
    user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    return await gamification_service.get_my_stats(db, tenant.id, user.id)


@router.get("/badges", response_model=list[BadgeListItem])
async def list_badges(
    tenant: Tenant = Depends(get_current_tenant),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await gamification_service.list_badges(db, tenant.id, _user.id)


@router.get("/hall-of-fame")
async def hall_of_fame(
    company_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await compute_monthly_hall_of_fame(db, company_id, tenant.id)
