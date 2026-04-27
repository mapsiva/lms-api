import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


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
