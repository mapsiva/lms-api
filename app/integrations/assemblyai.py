"""AssemblyAI integration for video transcription."""
from dataclasses import dataclass

import httpx

from app.core.config import get_settings


@dataclass(frozen=True)
class WordTimestamp:
    text: str
    start_ms: int
    end_ms: int


@dataclass(frozen=True)
class TranscriptStatus:
    id: str
    status: str  # "queued", "processing", "completed", "error"
    text: str | None = None


class AssemblyAIClient:
    _BASE_URL = "https://api.assemblyai.com/v2"

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.assemblyai_api_key.get_secret_value()
        self._headers = {"Authorization": self._api_key}

    async def submit_transcription(self, audio_url: str) -> str:
        """Submit audio/video URL for transcription. Returns transcript_id."""
        payload = {
            "audio_url": audio_url,
            "speaker_labels": False,
            "word_boost": [],
            "boost_param": "default",
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._BASE_URL}/transcript",
                headers=self._headers,
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        return data["id"]

    async def get_transcript_status(self, transcript_id: str) -> TranscriptStatus:
        """Poll transcript status."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._BASE_URL}/transcript/{transcript_id}",
                headers=self._headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        return TranscriptStatus(
            id=data["id"],
            status=data["status"],
            text=data.get("text"),
        )

    async def get_transcript_words(self, transcript_id: str) -> list[WordTimestamp]:
        """Fetch word-level timestamps. Returns empty list if not ready."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._BASE_URL}/transcript/{transcript_id}/words",
                headers=self._headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        words = data.get("words", [])
        return [
            WordTimestamp(
                text=w["text"],
                start_ms=int(w["start"]),
                end_ms=int(w["end"]),
            )
            for w in words
        ]

    async def get_full_transcript(self, transcript_id: str) -> dict | None:
        """Fetch full transcript with words for JSONB storage."""
        status = await self.get_transcript_status(transcript_id)
        if status.status != "completed":
            return None
        words = await self.get_transcript_words(transcript_id)
        return {
            "transcript_id": transcript_id,
            "full_text": status.text or "",
            "words": [
                {"text": w.text, "start_ms": w.start_ms, "end_ms": w.end_ms}
                for w in words
            ],
        }
