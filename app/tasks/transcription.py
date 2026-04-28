"""Celery tasks for transcription and summarization."""
import asyncio
import logging
import uuid

from redis import Redis as SyncRedis

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.integrations.assemblyai import AssemblyAIClient
from app.integrations.anthropic import AnthropicClient

logger = logging.getLogger(__name__)

PENDING_KEY = "transcription:pending"


@celery_app.task(bind=True, max_retries=3)
def transcribe_lesson_task(self, lesson_id: str, video_url: str) -> str:
    """Submit video to AssemblyAI for transcription. Store transcript_id in Redis pending set."""
    try:
        client = AssemblyAIClient()
        transcript_id = asyncio.run(client.submit_transcription(video_url))

        settings = get_settings()
        if settings.redis_url:
            redis = SyncRedis.from_url(settings.redis_url, decode_responses=True)
            try:
                redis.hset(PENDING_KEY, lesson_id, transcript_id)
            finally:
                redis.close()

        logger.info("Submitted transcription for lesson=%s transcript_id=%s", lesson_id, transcript_id)
        return transcript_id
    except Exception as exc:
        logger.exception("Transcription submission failed for lesson=%s", lesson_id)
        self.retry(countdown=60, exc=exc)
    return ""


@celery_app.task(bind=True, max_retries=3)
def summarize_lesson_task(self, lesson_id: str) -> str | None:
    """Fetch transcript and call Claude Haiku to generate summary. Save to lessons.ai_summary."""
    from app.core.sync_database import get_sync_db
    from app.models.course import Lesson

    db = get_sync_db()
    try:
        lesson = db.get(Lesson, uuid.UUID(lesson_id))
        if lesson is None:
            logger.warning("Lesson %s not found for summarization", lesson_id)
            return None

        transcript = lesson.transcript_text
        if not transcript:
            logger.warning("No transcript for lesson %s, skipping summary", lesson_id)
            return None

        full_text = transcript.get("full_text", "") if isinstance(transcript, dict) else str(transcript)
        if not full_text:
            logger.warning("Empty transcript text for lesson %s", lesson_id)
            return None

        anthropic = AnthropicClient()
        summary = asyncio.run(anthropic.generate_lesson_summary(full_text))

        lesson.ai_summary = summary
        db.commit()

        logger.info("Summary generated for lesson=%s", lesson_id)
        return summary
    except Exception as exc:
        logger.exception("Summarization failed for lesson=%s", lesson_id)
        self.retry(countdown=60, exc=exc)
        return None
    finally:
        db.close()
