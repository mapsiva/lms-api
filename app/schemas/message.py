"""Messaging schemas."""
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class LastMessagePreview(BaseModel):
    content: Optional[str] = None
    sender_id: Optional[str] = None
    created_at: Optional[str] = None


class ConversationListItem(BaseModel):
    id: str
    title: Optional[str]
    last_message: LastMessagePreview
    unread_count: int
    created_at: str


class ConversationListResponse(BaseModel):
    items: list[ConversationListItem]


class ConversationCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: Optional[str] = Field(None, max_length=255)
    participant_ids: list[uuid.UUID] = []


class ConversationCreateResponse(BaseModel):
    id: str


class MessageCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    content: str = Field(min_length=1)


class MessageCreateResponse(BaseModel):
    id: str


class MessageItem(BaseModel):
    id: str
    sender_id: str
    content: str
    created_at: str


class ConversationMessagesResponse(BaseModel):
    items: list[MessageItem]
