"""Messaging service."""
import json
import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.core.redis_client import get_redis
from app.models.messaging import Conversation, ConversationParticipant, Message


async def _get_conversation(
    db: AsyncSession, conversation_id: uuid.UUID, tenant_id: uuid.UUID
) -> Conversation:
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == tenant_id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise AppError(ErrorCode.CONVERSATION_NOT_FOUND)
    return conv


async def verify_conversation_participant(
    db: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    result = await db.execute(
        select(ConversationParticipant).where(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id == user_id,
        )
    )
    if not result.scalar_one_or_none():
        raise AppError(ErrorCode.CONVERSATION_NOT_FOUND)


async def get_conversation_or_404(
    db: AsyncSession, conversation_id: uuid.UUID, tenant_id: uuid.UUID, user_id: uuid.UUID
) -> Conversation:
    conv = await _get_conversation(db, conversation_id, tenant_id)
    await verify_conversation_participant(db, conversation_id, user_id)
    return conv


async def list_conversations(
    db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID
) -> list[dict]:
    result = await db.execute(
        select(Conversation, ConversationParticipant.last_read_at)
        .join(
            ConversationParticipant,
            ConversationParticipant.conversation_id == Conversation.id,
        )
        .where(
            Conversation.tenant_id == tenant_id,
            ConversationParticipant.user_id == user_id,
        )
        .order_by(Conversation.updated_at.desc())
    )
    rows = result.all()

    items = []
    for conv, last_read in rows:
        msg_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_msg = msg_result.scalar_one_or_none()

        unread = 0
        if last_msg and last_msg.sender_id != user_id:
            if last_read is None or last_msg.created_at > last_read:
                count_result = await db.execute(
                    select(func.count(Message.id)).where(
                        Message.conversation_id == conv.id,
                        Message.sender_id != user_id,
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

    return items


async def create_conversation(
    db: AsyncSession, tenant_id: uuid.UUID, creator_id: uuid.UUID, title: Optional[str], participant_ids: list[uuid.UUID]
) -> uuid.UUID:
    all_ids = set(participant_ids)
    all_ids.add(creator_id)

    conv = Conversation(tenant_id=tenant_id, title=title)
    db.add(conv)
    await db.commit()
    await db.refresh(conv)

    for pid in all_ids:
        cp = ConversationParticipant(conversation_id=conv.id, user_id=pid)
        db.add(cp)
    await db.commit()

    return conv.id


async def list_messages(
    db: AsyncSession, conversation_id: uuid.UUID
) -> list[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(50)
    )
    return list(result.scalars().all())


async def send_message(
    db: AsyncSession, tenant_id: uuid.UUID, conversation_id: uuid.UUID, sender_id: uuid.UUID, content: str, sender_name: str
) -> uuid.UUID:
    msg = Message(
        conversation_id=conversation_id,
        sender_id=sender_id,
        content=content,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    redis = get_redis()
    if redis:
        result = await db.execute(
            select(ConversationParticipant.user_id).where(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id != sender_id,
            )
        )
        recipients = [str(r) for r in result.scalars().all()]
        for recipient_id in recipients:
            await redis.publish(
                f"messages:{tenant_id}:{recipient_id}",
                json.dumps(
                    {
                        "conversation_id": str(conversation_id),
                        "message_id": str(msg.id),
                        "sender_id": str(sender_id),
                        "sender_name": sender_name,
                        "content": content[:200],
                        "created_at": msg.created_at.isoformat(),
                    }
                ),
            )

    return msg.id
