import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class NoteCreate(BaseModel):
    content: str = Field(min_length=1)
    video_timestamp_seconds: Optional[int] = None


class NoteUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1)
    video_timestamp_seconds: Optional[int] = None


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    lesson_id: uuid.UUID
    content: str
    video_timestamp_seconds: Optional[int]
    created_at: datetime
    updated_at: datetime
