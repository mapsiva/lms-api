"""Schemas for internal callback routes."""

from pydantic import BaseModel


class TranscriptionCallbackResponse(BaseModel):
    status: str
    lesson_id: str | None = None
