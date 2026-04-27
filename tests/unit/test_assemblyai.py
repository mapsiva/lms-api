"""Unit tests for AssemblyAI integration."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.assemblyai import AssemblyAIClient, TranscriptStatus, WordTimestamp


@pytest.fixture
def aai_client(monkeypatch):
    monkeypatch.setenv("ASSEMBLYAI_API_KEY", "test-key")
    with patch("app.integrations.assemblyai.get_settings") as mock_settings:
        settings = MagicMock()
        settings.assemblyai_api_key.get_secret_value.return_value = "test-key"
        mock_settings.return_value = settings
        yield AssemblyAIClient()


def test_word_timestamp_dataclass():
    w = WordTimestamp(text="hello", start_ms=100, end_ms=500)
    assert w.text == "hello"
    assert w.start_ms == 100
    assert w.end_ms == 500


def test_transcript_status_dataclass():
    ts = TranscriptStatus(id="t-123", status="completed", text="hello world")
    assert ts.id == "t-123"
    assert ts.status == "completed"
    assert ts.text == "hello world"


@pytest.mark.asyncio
async def test_submit_transcription(aai_client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"id": "t-123"}
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        tid = await aai_client.submit_transcription("https://example.com/audio.mp3")
    assert tid == "t-123"


@pytest.mark.asyncio
async def test_get_transcript_status(aai_client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"id": "t-123", "status": "completed", "text": "hello"}
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        ts = await aai_client.get_transcript_status("t-123")
    assert ts.status == "completed"
    assert ts.text == "hello"


@pytest.mark.asyncio
async def test_get_transcript_words(aai_client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "words": [
            {"text": "hello", "start": 100, "end": 400},
            {"text": "world", "start": 500, "end": 900},
        ]
    }
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        words = await aai_client.get_transcript_words("t-123")
    assert len(words) == 2
    assert words[0].text == "hello"
    assert words[0].start_ms == 100
    assert words[0].end_ms == 400


@pytest.mark.asyncio
async def test_get_full_transcript(aai_client):
    status_resp = MagicMock()
    status_resp.json.return_value = {"id": "t-123", "status": "completed", "text": "hello world"}
    status_resp.raise_for_status = MagicMock()

    words_resp = MagicMock()
    words_resp.json.return_value = {"words": [{"text": "hello", "start": 100, "end": 400}]}
    words_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.side_effect = [status_resp, words_resp]
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        full = await aai_client.get_full_transcript("t-123")
    assert full is not None
    assert full["full_text"] == "hello world"
    assert len(full["words"]) == 1
    assert full["words"][0]["text"] == "hello"


@pytest.mark.asyncio
async def test_get_full_transcript_not_ready(aai_client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"id": "t-123", "status": "processing"}
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        full = await aai_client.get_full_transcript("t-123")
    assert full is None
