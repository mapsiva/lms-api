import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.models.company import CompanyGoal, CompanyMember
from app.models.user import User
from app.schemas.manager import (
    DashboardGoalItem,
    GoalCreateRequest,
    GoalItem,
    GoalListResponse,
    ManagerDashboardResponse,
    ManagerReportResponse,
    MemberItem,
    MemberListResponse,
)


def require_manager(user: User) -> uuid.UUID:
    if user.role not in ("manager", "admin"):
        raise AppError(ErrorCode.MANAGER_REQUIRED)
    if not user.company_id:
        raise AppError(ErrorCode.NO_COMPANY_CONTEXT)
    return user.company_id


async def get_manager_dashboard(
    db: AsyncSession,
    company_id: uuid.UUID,
) -> ManagerDashboardResponse:
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

    return ManagerDashboardResponse(
        company_id=str(company_id),
        member_count=len(members),
        active_goals=len(goals),
        goals=[
            DashboardGoalItem(
                id=g.id,
                title=g.title,
                target_value=float(g.target_value),
            )
            for g in goals
        ],
    )


async def list_members(
    db: AsyncSession,
    company_id: uuid.UUID,
) -> MemberListResponse:
    result = await db.execute(
        select(User, CompanyMember)
        .join(CompanyMember, CompanyMember.user_id == User.id)
        .where(CompanyMember.company_id == company_id)
    )
    rows = result.all()
    return MemberListResponse(
        items=[
            MemberItem(
                user_id=str(u.id),
                email=u.email,
                name=u.name,
                team=cm.team,
                job_role=cm.job_role,
                is_active=cm.is_active,
            )
            for u, cm in rows
        ]
    )


async def create_goal(
    db: AsyncSession,
    company_id: uuid.UUID,
    data: GoalCreateRequest,
) -> uuid.UUID:
    goal = CompanyGoal(
        company_id=company_id,
        title=data.title,
        target_metric=data.target_metric,
        target_value=data.target_value,
        course_id=data.course_id,
        deadline=data.deadline,
    )
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return goal.id


async def list_goals(
    db: AsyncSession,
    company_id: uuid.UUID,
) -> GoalListResponse:
    result = await db.execute(
        select(CompanyGoal).where(CompanyGoal.company_id == company_id)
    )
    rows = result.scalars().all()
    return GoalListResponse(
        items=[
            GoalItem(
                id=g.id,
                title=g.title,
                target_metric=g.target_metric,
                target_value=float(g.target_value),
                status=g.status,
            )
            for g in rows
        ]
    )


async def send_goal_reminder(
    db: AsyncSession,
    company_id: uuid.UUID,
    goal_id: uuid.UUID,
) -> None:
    result = await db.execute(
        select(CompanyGoal).where(
            CompanyGoal.id == goal_id,
            CompanyGoal.company_id == company_id,
        )
    )
    goal = result.scalar_one_or_none()
    if not goal:
        raise AppError(ErrorCode.GOAL_NOT_FOUND)

    # Placeholder: dispatch notification Celery task
    return


async def manager_report(
    db: AsyncSession,
    company_id: uuid.UUID,
) -> ManagerReportResponse:
    result = await db.execute(
        select(CompanyMember).where(CompanyMember.company_id == company_id)
    )
    members = result.scalars().all()
    return ManagerReportResponse(
        member_count=len(members),
        company_id=str(company_id),
    )
