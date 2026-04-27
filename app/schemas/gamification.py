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
