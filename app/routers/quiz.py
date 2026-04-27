"""Quiz battle router."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, get_current_user
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.quiz import (
    BattleAnswerResponse,
    BattleAnswerSubmit,
    BattleCreate,
    BattleListItem,
)
from app.services import quiz as quiz_service

router = APIRouter(prefix="/quiz", tags=["quiz"])


@router.post("/battles", response_model=BattleListItem, status_code=201)
async def create_battle(
    body: BattleCreate,
    tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await quiz_service.create_battle(db, tenant.id, current_user, body)


@router.get("/battles", response_model=list[BattleListItem])
async def list_battles(
    tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await quiz_service.list_battles(db, tenant.id, current_user)


@router.get("/battles/{battle_id}")
async def get_battle(
    battle_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await quiz_service.get_battle(db, tenant.id, current_user, battle_id)


@router.post("/battles/{battle_id}/answer", response_model=BattleAnswerResponse)
async def submit_answer(
    battle_id: uuid.UUID,
    body: BattleAnswerSubmit,
    tenant: Tenant = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await quiz_service.submit_answer(db, tenant.id, current_user, battle_id, body)
