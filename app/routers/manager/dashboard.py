import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, get_current_user
from app.models.company import CompanyGoal, CompanyMember
from app.models.tenant import Tenant
from app.models.user import User

router = APIRouter(prefix="/manager", tags=["manager"])


def _require_manager(user: User):
    if user.role not in ("manager", "admin"):
        raise HTTPException(status_code=403, detail="Manager access required")
    if not user.company_id:
        raise HTTPException(status_code=403, detail="No company assigned")


@router.get("/dashboard")
async def manager_dashboard(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_manager(user)
    company_id = user.company_id

    result = await db.execute(
        select(CompanyMember).where(CompanyMember.company_id == company_id)
    )
    members = result.scalars().all()

    goals_result = await db.execute(
        select(CompanyGoal).where(
            CompanyGoal.company_id == company_id,
            CompanyGoal.status == "active",
        )
    )
    goals = goals_result.scalars().all()

    return {
        "company_id": str(company_id),
        "member_count": len(members),
        "active_goals": len(goals),
        "goals": [
            {"id": str(g.id), "title": g.title, "target_value": float(g.target_value)}
            for g in goals
        ],
    }


@router.get("/members")
async def list_members(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_manager(user)
    result = await db.execute(
        select(User, CompanyMember)
        .join(CompanyMember, CompanyMember.user_id == User.id)
        .where(CompanyMember.company_id == user.company_id)
    )
    rows = result.all()
    return {
        "items": [
            {
                "user_id": str(u.id),
                "email": u.email,
                "name": u.name,
                "team": cm.team,
                "job_role": cm.job_role,
                "is_active": cm.is_active,
            }
            for u, cm in rows
        ]
    }


@router.post("/goals", status_code=201)
async def create_goal(
    body: dict[str, Any],
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_manager(user)
    goal = CompanyGoal(
        company_id=user.company_id,
        title=body["title"],
        target_metric=body["target_metric"],
        target_value=body["target_value"],
        course_id=body.get("course_id"),
        deadline=body.get("deadline"),
    )
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return {"id": str(goal.id)}


@router.get("/goals")
async def list_goals(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_manager(user)
    result = await db.execute(
        select(CompanyGoal).where(CompanyGoal.company_id == user.company_id)
    )
    rows = result.scalars().all()
    return {
        "items": [
            {
                "id": str(g.id),
                "title": g.title,
                "target_metric": g.target_metric,
                "target_value": float(g.target_value),
                "status": g.status,
            }
            for g in rows
        ]
    }


@router.post("/goals/{goal_id}/reminder")
async def send_goal_reminder(
    goal_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_manager(user)
    result = await db.execute(
        select(CompanyGoal).where(
            CompanyGoal.id == goal_id,
            CompanyGoal.company_id == user.company_id,
        )
    )
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    # Placeholder: dispatch notification Celery task
    return {"status": "dispatched"}


@router.get("/report")
async def manager_report(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_manager(user)
    result = await db.execute(
        select(CompanyMember).where(CompanyMember.company_id == user.company_id)
    )
    members = result.scalars().all()
    return {"member_count": len(members), "company_id": str(user.company_id)}
