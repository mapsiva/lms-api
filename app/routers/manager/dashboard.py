import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, get_current_user
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.manager import (
    GoalCreateRequest,
    GoalCreateResponse,
    GoalListResponse,
    GoalReminderResponse,
    ManagerDashboardResponse,
    MemberListResponse,
)
from app.services import manager as manager_service

router = APIRouter(prefix="/manager", tags=["manager"])


@router.get("/dashboard", response_model=ManagerDashboardResponse)
async def manager_dashboard(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company_id = manager_service.require_manager(user)
    return await manager_service.get_manager_dashboard(db, company_id)


@router.get("/members", response_model=MemberListResponse)
async def list_members(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company_id = manager_service.require_manager(user)
    return await manager_service.list_members(db, company_id)


@router.post("/goals", status_code=201, response_model=GoalCreateResponse)
async def create_goal(
    body: GoalCreateRequest,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company_id = manager_service.require_manager(user)
    goal_id = await manager_service.create_goal(db, company_id, body)
    return GoalCreateResponse(id=str(goal_id))


@router.get("/goals", response_model=GoalListResponse)
async def list_goals(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company_id = manager_service.require_manager(user)
    return await manager_service.list_goals(db, company_id)


@router.post("/goals/{goal_id}/reminder", response_model=GoalReminderResponse)
async def send_goal_reminder(
    goal_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company_id = manager_service.require_manager(user)
    await manager_service.send_goal_reminder(db, company_id, goal_id)
    return GoalReminderResponse(status="dispatched")


@router.get("/report")
async def manager_report(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    company_id = manager_service.require_manager(user)
    return await manager_service.manager_report(db, company_id)
