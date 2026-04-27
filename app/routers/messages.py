"""Messaging REST router."""
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_tenant, get_current_user
from app.models.messaging import Conversation, ConversationParticipant, Message
from app.models.tenant import Tenant
from app.models.user import User

router = APIRouter(prefix="/messages", tags=["messages"])


async def _get_conversation_or_404(
    db: AsyncSession, conversation_id: uuid.UUID, tenant_id: uuid.UUID, user_id: uuid.UUID
):
    result = await db.execute(
        select(Conversation)
        .where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == tenant_id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    # Verify user is participant
    result = await db.execute(
        select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id == user_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.get("/conversations")
async def list_conversations(
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Get conversations where user is participant
    result = await db.execute(
        select(Conversation, ConversationParticipant.last_read_at)
        .join(
            ConversationParticipant,
            ConversationParticipant.conversation_id == Conversation.id,
        )
        .where(
            Conversation.tenant_id == tenant.id,
            ConversationParticipant.user_id == user.id,
        )
        .order_by(Conversation.updated_at.desc())
    )
    rows = result.all()

    items = []
    for conv, last_read in rows:
        # Last message preview
        msg_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_msg = msg_result.scalar_one_or_none()

        # Unread count
        unread = 0
        if last_msg and last_msg.sender_id != user.id:
            if last_read is None or last_msg.created_at > last_read:
                count_result = await db.execute(
                    select(func.count(Message.id)).where(
                        Message.conversation_id == conv.id,
                        Message.sender_id != user.id,
                        (last_read is None) | (Message.created_at > last_read),
                    )
                )
                unread = count_result.scalar() or 0

        items.append(
            {
                "id": str(conv.id),
                "title": conv.title,
                "last_message": {
                    "content": last_msg.content[:120] if last_msg else None,
                    "sender_id": str(last_msg.sender_id) if last_msg else None,
                    "created_at": last_msg.created_at.isoformat() if last_msg else None,
                },
                "unread_count": unread,
                "created_at": conv.created_at.isoformat(),
            }
        )

    return {"items": items}


@router.post("/conversations", status_code=201)
async def create_conversation(
    body: dict[str, Any],
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    title = body.get("title")
    participant_ids = set(body.get("participant_ids", []))
    participant_ids.add(str(user.id))

    conv = Conversation(tenant_id=tenant.id, title=title)
    db.add(conv)
    await db.commit()
    await db.refresh(conv)

    for pid in participant_ids:
        cp = ConversationParticipant(
            conversation_id=conv.id,
            user_id=uuid.UUID(pid),
        )
        db.add(cp)
    await db.commit()

    return {"id": str(conv.id)}


@router.get("/conversations/{conversation_id}/messages")
async def list_messages(
    conversation_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_conversation_or_404(db, conversation_id, tenant.id, user.id)

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(50)
    )
    rows = result.scalars().all()
    return {
        "items": [
            {
                "id": str(m.id),
                "sender_id": str(m.sender_id),
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in reversed(rows)
        ]
    }


@router.post("/conversations/{conversation_id}/messages", status_code=201)
async def send_message(
    conversation_id: uuid.UUID,
    body: dict[str, Any],
    tenant: Tenant = Depends(get_current_tenant),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_conversation_or_404(db, conversation_id, tenant.id, user.id)

    content = body.get("content", "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Content required")

    msg = Message(
        conversation_id=conversation_id,
        sender_id=user.id,
        content=content,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    # Dispatch notification via Redis pub/sub
    from app.core.redis_client import get_redis

    redis = get_redis()
    if redis:
        import json

        # Get other participants
        result = await db.execute(
            select(ConversationParticipant.user_id).where(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id != user.id,
            )
        )
        recipients = [str(r) for r in result.scalars().all()]
        for recipient_id in recipients:
            await redis.publish(
                f"messages:{tenant.id}:{recipient_id}",
                json.dumps(
                    {
                        "conversation_id": str(conversation_id),
                        "message_id": str(msg.id),
                        "sender_id": str(user.id),
                        "sender_name": user.name,
                        "content": content[:200],
                        "created_at": msg.created_at.isoformat(),
                    }
                ),
            )

    return {"id": str(msg.id)}
