"""Unit tests for Groq integration."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.groq import GroqClient, ModerationResult


@pytest.fixture
def groq_client():
    with patch("app.integrations.groq.get_settings") as mock_settings:
        settings = MagicMock()
        settings.groq_api_key.get_secret_value.return_value = "test-groq-key"
        settings.groq_model = "llama-3.3-70b-versatile"
        mock_settings.return_value = settings
        yield GroqClient()


def _mock_response(content: str) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = {
        "choices": [{"message": {"content": content}}]
    }
    resp.raise_for_status = MagicMock()
    return resp


def test_moderation_result_dataclass():
    mr = ModerationResult(score=0.9, flagged=True, reason="spam")
    assert mr.score == 0.9
    assert mr.flagged is True
    assert mr.reason == "spam"


@pytest.mark.asyncio
async def test_generate_lesson_summary(groq_client):
    mock_resp = _mock_response("- Ponto A\n- Ponto B")

    with patch("app.integrations.groq.httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_http

        summary = await groq_client.generate_lesson_summary("transcript here")

    assert summary == "- Ponto A\n- Ponto B"
    mock_http.post.assert_awaited_once()
    call_kwargs = mock_http.post.call_args
    payload = call_kwargs.kwargs["json"]
    assert payload["model"] == "llama-3.3-70b-versatile"
    assert payload["max_tokens"] == 512
    assert any(m["role"] == "system" for m in payload["messages"])


@pytest.mark.asyncio
async def test_generate_lesson_summary_empty_choices(groq_client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"choices": []}
    mock_resp.raise_for_status = MagicMock()

    with patch("app.integrations.groq.httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_http

        summary = await groq_client.generate_lesson_summary("anything")

    assert summary == ""


@pytest.mark.asyncio
async def test_moderate_content_flagged(groq_client):
    mock_resp = _mock_response('{"score": 0.85, "flagged": true, "reason": "toxic"}')

    with patch("app.integrations.groq.httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_http

        result = await groq_client.moderate_content("bad content")

    assert result.flagged is True
    assert result.score == 0.85
    assert result.reason == "toxic"


@pytest.mark.asyncio
async def test_moderate_content_safe(groq_client):
    mock_resp = _mock_response('{"score": 0.1, "flagged": false, "reason": ""}')

    with patch("app.integrations.groq.httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_http

        result = await groq_client.moderate_content("nice content")

    assert result.flagged is False
    assert result.score == 0.1


@pytest.mark.asyncio
async def test_moderate_content_auto_flag_threshold(groq_client):
    mock_resp = _mock_response('{"score": 0.75, "flagged": false, "reason": "borderline"}')

    with patch("app.integrations.groq.httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_http

        result = await groq_client.moderate_content("borderline")

    assert result.flagged is True
    assert result.score == 0.75


@pytest.mark.asyncio
async def test_moderate_content_parse_error(groq_client):
    mock_resp = _mock_response("not json at all")

    with patch("app.integrations.groq.httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_http

        result = await groq_client.moderate_content("whatever")

    assert result.flagged is False
    assert result.score == 0.0
    assert result.reason == "parse error"


@pytest.mark.asyncio
async def test_moderate_content_empty_response(groq_client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"choices": []}
    mock_resp.raise_for_status = MagicMock()

    with patch("app.integrations.groq.httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_http

        result = await groq_client.moderate_content("whatever")

    assert result.flagged is False
    assert result.score == 0.0
    assert result.reason == "empty response"


@pytest.mark.asyncio
async def test_moderate_content_json_in_markdown(groq_client):
    raw = '```json\n{"score": 0.9, "flagged": true, "reason": "spam"}\n```'
    mock_resp = _mock_response(raw)

    with patch("app.integrations.groq.httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_http

        result = await groq_client.moderate_content("spam content")

    assert result.flagged is True
    assert result.score == 0.9


@pytest.mark.asyncio
async def test_request_headers_contain_auth(groq_client):
    mock_resp = _mock_response("- summary")

    with patch("app.integrations.groq.httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_http

        await groq_client.generate_lesson_summary("t")

    call_kwargs = mock_http.post.call_args
    headers = call_kwargs.kwargs["headers"]
    assert headers["Authorization"] == "Bearer test-groq-key"
    assert "https://api.groq.com/openai/v1" in call_kwargs.args[0]
