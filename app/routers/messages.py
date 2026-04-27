"""Messaging REST router."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, get_current_user
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.message import (
    ConversationCreate,
    ConversationCreateResponse,
    ConversationListResponse,
    ConversationMessagesResponse,
    MessageCreate,
    MessageCreateResponse,
    MessageItem,
)
from app.services import message as message_service

router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items = await message_service.list_conversations(db, tenant.id, user.id)
    return {"items": items}


@router.post("/conversations", status_code=201, response_model=ConversationCreateResponse)
async def create_conversation(
    body: ConversationCreate,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    conv_id = await message_service.create_conversation(
        db,
        tenant_id=tenant.id,
        creator_id=user.id,
        title=body.title,
        participant_ids=body.participant_ids,
    )
    return {"id": str(conv_id)}


@router.get("/conversations/{conversation_id}/messages", response_model=ConversationMessagesResponse)
async def list_messages(
    conversation_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await message_service.get_conversation_or_404(db, conversation_id, tenant.id, user.id)
    rows = await message_service.list_messages(db, conversation_id)
    return {
        "items": [
            MessageItem(
                id=str(m.id),
                sender_id=str(m.sender_id),
                content=m.content,
                created_at=m.created_at.isoformat(),
            )
            for m in reversed(rows)
        ]
    }


@router.post("/conversations/{conversation_id}/messages", status_code=201, response_model=MessageCreateResponse)
async def send_message(
    conversation_id: uuid.UUID,
    body: MessageCreate,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await message_service.get_conversation_or_404(db, conversation_id, tenant.id, user.id)
    msg_id = await message_service.send_message(
        db,
        tenant_id=tenant.id,
        conversation_id=conversation_id,
        sender_id=user.id,
        content=body.content,
        sender_name=user.name,
    )
    return {"id": str(msg_id)}
