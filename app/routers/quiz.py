"""Quiz battle router."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.core.database import get_db
from app.core.dependencies import get_current_tenant, get_current_user
from app.models.quiz import QuizBattle, QuizBattleAnswer
from app.models.user import User

router = APIRouter(prefix="/quiz", tags=["quiz"])

# ── Hardcoded MVP trivia questions ───────────────────────────────────────────

_DEFAULT_QUESTIONS: list[dict[str, Any]] = [
    {
        "question": "Qual é a capital da França?",
        "choices": ["Londres", "Berlim", "Paris", "Madri"],
        "correct_index": 2,
    },
    {
        "question": "Quanto é 7 x 8?",
        "choices": ["54", "56", "48", "64"],
        "correct_index": 1,
    },
    {
        "question": "Qual planeta é conhecido como planeta vermelho?",
        "choices": ["Vênus", "Marte", "Júpiter", "Saturno"],
        "correct_index": 1,
    },
    {
        "question": "Em que ano o Brasil foi descoberto?",
        "choices": ["1498", "1500", "1502", "1492"],
        "correct_index": 1,
    },
    {
        "question": "Qual é o maior oceano da Terra?",
        "choices": ["Atlântico", "Índico", "Ártico", "Pacífico"],
        "correct_index": 3,
    },
]


# ── Schemas ──────────────────────────────────────────────────────────────────


class BattleCreate(BaseModel):
    opponent_id: uuid.UUID
    course_id: Optional[uuid.UUID] = None


class BattleListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    challenger_id: uuid.UUID
    opponent_id: uuid.UUID
    course_id: Optional[uuid.UUID]
    status: str
    winner_id: Optional[uuid.UUID]
    expires_at: datetime
    created_at: datetime


class BattleAnswerSubmit(BaseModel):
    answers: dict[str, int]


class BattleAnswerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    battle_id: uuid.UUID
    user_id: uuid.UUID
    score: int
    created_at: datetime


class BattleDetailResponse(BaseModel):
    id: uuid.UUID
    challenger_id: uuid.UUID
    opponent_id: uuid.UUID
    course_id: Optional[uuid.UUID]
    status: str
    winner_id: Optional[uuid.UUID]
    expires_at: datetime
    created_at: datetime
    questions: list[dict[str, Any]]
    challenger_answer: Optional[BattleAnswerResponse]
    opponent_answer: Optional[BattleAnswerResponse]


# ── Helpers ──────────────────────────────────────────────────────────────────


def _calculate_score(questions: list[dict[str, Any]], answers: dict[str, int]) -> int:
    score = 0
    for idx, q in enumerate(questions):
        key = str(idx)
        if key in answers and answers[key] == q.get("correct_index"):
            score += 1
    return score


def _strip_correct_answers(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"question": q["question"], "choices": q["choices"]} for q in questions
    ]


async def _maybe_expire_battle(battle: QuizBattle) -> bool:
    """Mark battle as expired if past due. Returns True if expired."""
    now = datetime.now(timezone.utc)
    if battle.status in ("pending", "active") and battle.expires_at < now:
        battle.status = "expired"
        return True
    return False


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/battles", response_model=BattleListItem, status_code=201)
async def create_battle(
    body: BattleCreate,
    tenant=Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validate opponent exists and belongs to same tenant
    opponent_result = await db.execute(
        select(User).where(User.id == body.opponent_id, User.tenant_id == tenant.id)
    )
    opponent = opponent_result.scalar_one_or_none()
    if opponent is None:
        raise HTTPException(status_code=404, detail="Opponent not found")

    if body.opponent_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot challenge yourself")

    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

    battle = QuizBattle(
        tenant_id=tenant.id,
        challenger_id=current_user.id,
        opponent_id=body.opponent_id,
        course_id=body.course_id,
        questions=list(_DEFAULT_QUESTIONS),
        status="pending",
        expires_at=expires_at,
    )
    db.add(battle)
    await db.commit()
    await db.refresh(battle)
    return battle


@router.get("/battles", response_model=list[BattleListItem])
async def list_battles(
    tenant=Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(QuizBattle)
        .where(
            QuizBattle.tenant_id == tenant.id,
            (QuizBattle.challenger_id == current_user.id)
            | (QuizBattle.opponent_id == current_user.id),
        )
        .order_by(QuizBattle.created_at.desc())
    )
    battles = result.scalars().all()

    now = datetime.now(timezone.utc)
    for battle in battles:
        if battle.status in ("pending", "active") and battle.expires_at < now:
            battle.status = "expired"

    await db.commit()
    return battles


@router.get("/battles/{battle_id}", response_model=BattleDetailResponse)
async def get_battle(
    battle_id: uuid.UUID,
    tenant=Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    battle = await db.get(QuizBattle, battle_id)
    if battle is None or battle.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Battle not found")

    if battle.challenger_id != current_user.id and battle.opponent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if await _maybe_expire_battle(battle):
        await db.commit()

    # Fetch answers from both players
    answers_result = await db.execute(
        select(QuizBattleAnswer).where(QuizBattleAnswer.battle_id == battle.id)
    )
    answers = answers_result.scalars().all()

    challenger_answer: Optional[QuizBattleAnswer] = None
    opponent_answer: Optional[QuizBattleAnswer] = None
    for ans in answers:
        if ans.user_id == battle.challenger_id:
            challenger_answer = ans
        elif ans.user_id == battle.opponent_id:
            opponent_answer = ans

    questions = battle.questions or []
    if battle.status != "completed":
        questions = _strip_correct_answers(questions)

    return BattleDetailResponse(
        id=battle.id,
        challenger_id=battle.challenger_id,
        opponent_id=battle.opponent_id,
        course_id=battle.course_id,
        status=battle.status,
        winner_id=battle.winner_id,
        expires_at=battle.expires_at,
        created_at=battle.created_at,
        questions=questions,
        challenger_answer=BattleAnswerResponse.model_validate(challenger_answer) if challenger_answer else None,
        opponent_answer=BattleAnswerResponse.model_validate(opponent_answer) if opponent_answer else None,
    )


@router.post("/battles/{battle_id}/answer", response_model=BattleAnswerResponse)
async def submit_answer(
    battle_id: uuid.UUID,
    body: BattleAnswerSubmit,
    tenant=Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    battle = await db.get(QuizBattle, battle_id)
    if battle is None or battle.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Battle not found")

    if battle.challenger_id != current_user.id and battle.opponent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if await _maybe_expire_battle(battle):
        await db.commit()
        raise HTTPException(status_code=400, detail="Battle has expired")

    if battle.status == "completed":
        raise HTTPException(status_code=400, detail="Battle already completed")

    # Prevent duplicate answers
    existing_result = await db.execute(
        select(QuizBattleAnswer).where(
            QuizBattleAnswer.battle_id == battle.id,
            QuizBattleAnswer.user_id == current_user.id,
        )
    )
    if existing_result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="Already answered")

    questions = battle.questions or []
    score = _calculate_score(questions, body.answers)

    answer = QuizBattleAnswer(
        battle_id=battle.id,
        user_id=current_user.id,
        answers=dict(body.answers),
        score=score,
    )
    db.add(answer)

    # Update battle status
    if battle.status == "pending":
        battle.status = "active"

    await db.commit()
    await db.refresh(answer)

    # Check if both players have answered
    all_answers_result = await db.execute(
        select(QuizBattleAnswer).where(QuizBattleAnswer.battle_id == battle.id)
    )
    all_answers = all_answers_result.scalars().all()

    if len(all_answers) == 2:
        # Determine winner
        challenger_answer = next(
            (a for a in all_answers if a.user_id == battle.challenger_id), None
        )
        opponent_answer = next(
            (a for a in all_answers if a.user_id == battle.opponent_id), None
        )

        if challenger_answer and opponent_answer:
            if challenger_answer.score > opponent_answer.score:
                battle.winner_id = battle.challenger_id
            elif opponent_answer.score > challenger_answer.score:
                battle.winner_id = battle.opponent_id
            else:
                # Tie — no winner
                battle.winner_id = None
            battle.status = "completed"
            await db.commit()

            # Award XP to winner
            if battle.winner_id:
                winner_result = await db.execute(
                    select(User).where(
                        User.id == battle.winner_id, User.tenant_id == tenant.id
                    )
                )
                winner = winner_result.scalar_one_or_none()
                company_id_str = str(winner.company_id) if winner and winner.company_id else None
                celery_app.send_task(
                    "app.tasks.gamification.award_xp_task",
                    args=[
                        str(battle.winner_id),
                        str(tenant.id),
                        company_id_str,
                        "quiz_battle_won",
                        str(battle.id),
                        "quiz_battle",
                    ],
                )

    return answer
