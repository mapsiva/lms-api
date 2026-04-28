import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class LeaderboardEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rank: int
    user_id: str
    name: str
    total_xp: int
    badges: int


class TopBadge(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    rarity: str
    awarded_at: str


class MyStatsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_xp: int
    level: int
    current_streak: int
    longest_streak: int
    top_badges: list[TopBadge]


class BadgeListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    category: str
    rarity: str
    earned: bool


# ── Admin schemas ─────────────────────────────────────────────────────────────

class BadgeCreate(BaseModel):
    name: str
    description: str | None = None
    category: Literal["behavior", "completion", "social", "event"]
    rarity: Literal["common", "rare", "epic", "legendary"]
    icon_url: str | None = None
    rule_event: str | None = None
    rule_conditions: dict | None = None
    xp_reward: int = 0


class BadgeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    icon_url: str | None = None
    rule_event: str | None = None
    rule_conditions: dict | None = None
    xp_reward: int | None = None
    is_active: bool | None = None


class BadgeAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    category: str
    rarity: str
    icon_url: str | None
    rule_event: str | None
    rule_conditions: dict | None
    xp_reward: int
    is_active: bool
    created_at: datetime


class SpecialEventCreate(BaseModel):
    name: str
    event_type: Literal["xp_multiplier", "double_xp", "bonus_badge"]
    xp_multiplier: int | None = None
    company_id: uuid.UUID | None = None
    starts_at: datetime
    ends_at: datetime


class SpecialEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    event_type: str
    xp_multiplier: int | None
    company_id: uuid.UUID | None
    starts_at: datetime
    ends_at: datetime
    is_active: bool
