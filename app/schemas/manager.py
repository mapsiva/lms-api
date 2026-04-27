import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class GoalItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    target_metric: str
    target_value: float
    status: str


class DashboardGoalItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    target_value: float


class ManagerDashboardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    company_id: str
    member_count: int
    active_goals: int
    goals: list[DashboardGoalItem]


class MemberItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    email: str
    name: str
    team: Optional[str]
    job_role: Optional[str]
    is_active: bool


class MemberListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[MemberItem]


class GoalCreateRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str = Field(min_length=1, max_length=255)
    target_metric: str
    target_value: float
    course_id: Optional[uuid.UUID] = None
    deadline: Optional[datetime] = None


class GoalCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str


class GoalListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[GoalItem]


class GoalReminderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str


class ManagerReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    member_count: int
    company_id: str
