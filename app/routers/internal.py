"""Internal callback routes (not public API)."""
import logging
import uuid

from fastapi import APIRouter, HTTPException, Request

from app.core.config import get_settings
from app.core.celery_app import celery_app
from app.core.database import get_db
from app.core.redis_client import get_redis
from app.integrations.assemblyai import AssemblyAIClient
from app.models.course import Lesson

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/internal", tags=["internal"])
PENDING_KEY = "transcription:pending"


@router.post("/transcription-callback")
async def transcription_callback(request: Request):
    """AssemblyAI webhook callback: save transcript, trigger summary."""
    auth_header = request.headers.get("authorization", "")

    # AssemblyAI does not always send auth headers; basic check if key present
    api_key = get_settings().assemblyai_api_key.get_secret_value()
    if api_key and auth_header and auth_header != f"Bearer {api_key}":
        raise HTTPException(status_code=401, detail="Invalid auth")

    body = await request.json()
    transcript_id = body.get("transcript_id")
    if not transcript_id:
        raise HTTPException(status_code=400, detail="Missing transcript_id")

    client = AssemblyAIClient()
    full = await client.get_full_transcript(transcript_id)
    if full is None:
        raise HTTPException(status_code=202, detail="Transcript not ready")

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
        raise HTTPException(status_code=404, detail="No pending lesson")

    async for session in get_db():
        lesson = await session.get(Lesson, uuid.UUID(lesson_id))
        if lesson is None:
            raise HTTPException(status_code=404, detail="Lesson not found")
        lesson.transcript_text = full
        await session.commit()
        break

    # Remove from pending
    await redis.hdel(PENDING_KEY, lesson_id)  # type: ignore[misc]

    # Trigger summary
    celery_app.send_task("app.tasks.transcription.summarize_lesson_task", args=[lesson_id])

    return {"status": "ok", "lesson_id": lesson_id}
