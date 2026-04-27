"""Unit tests for Anthropic (Claude) integration."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.anthropic import AnthropicClient, ModerationResult


@pytest.fixture
def anthropic_client(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    with patch("app.integrations.anthropic.get_settings") as mock_settings:
        settings = MagicMock()
        settings.anthropic_api_key.get_secret_value.return_value = "test-key"
        mock_settings.return_value = settings
        yield AnthropicClient()


def test_moderation_result():
    mr = ModerationResult(score=0.8, flagged=True, reason="toxic")
    assert mr.score == 0.8
    assert mr.flagged is True
    assert mr.reason == "toxic"


@pytest.mark.asyncio
async def test_generate_lesson_summary(anthropic_client):
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text="- Ponto 1\n- Ponto 2")]

    anthropic_client._client.messages.create = AsyncMock(return_value=mock_msg)

    summary = await anthropic_client.generate_lesson_summary("transcript here")
    assert summary == "- Ponto 1\n- Ponto 2"
    anthropic_client._client.messages.create.assert_awaited_once()
    call = anthropic_client._client.messages.create.call_args
    assert call.kwargs["max_tokens"] == 512


@pytest.mark.asyncio
async def test_moderate_content_flagged(anthropic_client):
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text='{"score": 0.85, "flagged": true, "reason": "toxic"}')]

    anthropic_client._client.messages.create = AsyncMock(return_value=mock_msg)

    result = await anthropic_client.moderate_content("bad words")
    assert result.flagged is True
    assert result.score == 0.85
    assert result.reason == "toxic"


@pytest.mark.asyncio
async def test_moderate_content_safe(anthropic_client):
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text='{"score": 0.1, "flagged": false, "reason": ""}')]

    anthropic_client._client.messages.create = AsyncMock(return_value=mock_msg)

    result = await anthropic_client.moderate_content("nice words")
    assert result.flagged is False
    assert result.score == 0.1


@pytest.mark.asyncio
async def test_moderate_content_parse_error(anthropic_client):
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text="invalid json")]

    anthropic_client._client.messages.create = AsyncMock(return_value=mock_msg)

    result = await anthropic_client.moderate_content("whatever")
    assert result.flagged is False
    assert result.score == 0.0
    assert result.reason == "parse error"


@pytest.mark.asyncio
async def test_moderate_content_empty_response(anthropic_client):
    mock_msg = MagicMock()
    mock_msg.content = []

    anthropic_client._client.messages.create = AsyncMock(return_value=mock_msg)

    result = await anthropic_client.moderate_content("whatever")
    assert result.flagged is False
    assert result.score == 0.0
    assert result.reason == "empty response"


@pytest.mark.asyncio
async def test_moderate_content_auto_flag_threshold(anthropic_client):
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text='{"score": 0.75, "flagged": false, "reason": ""}')]

    anthropic_client._client.messages.create = AsyncMock(return_value=mock_msg)

    result = await anthropic_client.moderate_content("borderline")
    assert result.flagged is True  # auto-flagged because score >= 0.7
    assert result.score == 0.75
