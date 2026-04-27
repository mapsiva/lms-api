"""Internal callback business logic."""

import logging
import uuid

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.core.database import get_db
from app.core.error_codes import ErrorCode
from app.core.errors import AppError
from app.core.redis_client import get_redis
from app.integrations.assemblyai import AssemblyAIClient
from app.models.course import Lesson

logger = logging.getLogger(__name__)
PENDING_KEY = "transcription:pending"


async def process_transcription_callback(*, auth_header: str, body: dict) -> dict:
    """Process AssemblyAI transcription webhook callback."""
    api_key = get_settings().assemblyai_api_key.get_secret_value()
    if api_key and auth_header and auth_header != f"Bearer {api_key}":
        raise AppError(ErrorCode.INTERNAL_AUTH_INVALID)

    transcript_id = body.get("transcript_id")
    if not transcript_id:
        raise AppError(ErrorCode.MISSING_TRANSCRIPT_ID)

    client = AssemblyAIClient()
    full = await client.get_full_transcript(transcript_id)
    if full is None:
        raise AppError(ErrorCode.TRANSCRIPT_NOT_READY)

    redis = get_redis()
    assert redis is not None
    lesson_id = None
    pending = await redis.hgetall(PENDING_KEY)  # type: ignore[misc]
    for lid, tid in pending.items():
        if tid == transcript_id:
            lesson_id = lid
            break

    if lesson_id is None:
        logger.warning("No pending lesson for transcript_id=%s", transcript_id)
        raise AppError(ErrorCode.NO_PENDING_LESSON)

    async for session in get_db():
        lesson = await session.get(Lesson, uuid.UUID(lesson_id))
        if lesson is None:
            raise AppError(ErrorCode.LESSON_NOT_FOUND)
        lesson.transcript_text = full
        await session.commit()
        break

    await redis.hdel(PENDING_KEY, lesson_id)  # type: ignore[misc]

    celery_app.send_task(
        "app.tasks.transcription.summarize_lesson_task", args=[lesson_id]
    )

    return {"status": "ok", "lesson_id": lesson_id}
