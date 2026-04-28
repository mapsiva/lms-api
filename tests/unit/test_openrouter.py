"""Unit tests for OpenRouter integration."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.openrouter import ModerationResult, OpenRouterClient


@pytest.fixture
def openrouter_client():
    with patch("app.integrations.openrouter.get_settings") as mock_settings:
        settings = MagicMock()
        settings.openrouter_api_key.get_secret_value.return_value = "test-or-key"
        settings.openrouter_model = "meta-llama/llama-3.1-8b-instruct:free"
        settings.openrouter_site_url = "https://example.com"
        settings.openrouter_app_name = "LMS"
        mock_settings.return_value = settings
        yield OpenRouterClient()


def _mock_response(content: str) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = {
        "choices": [{"message": {"content": content}}]
    }
    resp.raise_for_status = MagicMock()
    return resp


def test_moderation_result_dataclass():
    mr = ModerationResult(score=0.5, flagged=False, reason="ok")
    assert mr.score == 0.5
    assert mr.flagged is False
    assert mr.reason == "ok"


@pytest.mark.asyncio
async def test_generate_lesson_summary(openrouter_client):
    mock_resp = _mock_response("- Tópico 1\n- Tópico 2")

    with patch("app.integrations.openrouter.httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_http

        summary = await openrouter_client.generate_lesson_summary("transcript")

    assert summary == "- Tópico 1\n- Tópico 2"
    payload = mock_http.post.call_args.kwargs["json"]
    assert payload["model"] == "meta-llama/llama-3.1-8b-instruct:free"
    assert payload["max_tokens"] == 512


@pytest.mark.asyncio
async def test_generate_lesson_summary_empty_choices(openrouter_client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"choices": []}
    mock_resp.raise_for_status = MagicMock()

    with patch("app.integrations.openrouter.httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_http

        summary = await openrouter_client.generate_lesson_summary("anything")

    assert summary == ""


@pytest.mark.asyncio
async def test_moderate_content_flagged(openrouter_client):
    mock_resp = _mock_response('{"score": 0.9, "flagged": true, "reason": "hate speech"}')

    with patch("app.integrations.openrouter.httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_http

        result = await openrouter_client.moderate_content("hateful text")

    assert result.flagged is True
    assert result.score == 0.9
    assert result.reason == "hate speech"


@pytest.mark.asyncio
async def test_moderate_content_safe(openrouter_client):
    mock_resp = _mock_response('{"score": 0.05, "flagged": false, "reason": "clean"}')

    with patch("app.integrations.openrouter.httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_http

        result = await openrouter_client.moderate_content("good content")

    assert result.flagged is False
    assert result.score == 0.05


@pytest.mark.asyncio
async def test_moderate_content_auto_flag_threshold(openrouter_client):
    mock_resp = _mock_response('{"score": 0.72, "flagged": false, "reason": "borderline"}')

    with patch("app.integrations.openrouter.httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_http

        result = await openrouter_client.moderate_content("borderline")

    assert result.flagged is True
    assert result.score == 0.72


@pytest.mark.asyncio
async def test_moderate_content_parse_error(openrouter_client):
    mock_resp = _mock_response("I cannot determine toxicity")

    with patch("app.integrations.openrouter.httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_http

        result = await openrouter_client.moderate_content("whatever")

    assert result.flagged is False
    assert result.score == 0.0
    assert result.reason == "parse error"


@pytest.mark.asyncio
async def test_moderate_content_empty_response(openrouter_client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"choices": []}
    mock_resp.raise_for_status = MagicMock()

    with patch("app.integrations.openrouter.httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_http

        result = await openrouter_client.moderate_content("whatever")

    assert result.flagged is False
    assert result.score == 0.0
    assert result.reason == "empty response"


@pytest.mark.asyncio
async def test_moderate_content_json_in_markdown(openrouter_client):
    raw = '```\n{"score": 0.8, "flagged": true, "reason": "explicit"}\n```'
    mock_resp = _mock_response(raw)

    with patch("app.integrations.openrouter.httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_http

        result = await openrouter_client.moderate_content("explicit content")

    assert result.flagged is True
    assert result.score == 0.8


@pytest.mark.asyncio
async def test_request_headers_contain_auth_and_routing(openrouter_client):
    mock_resp = _mock_response("- summary")

    with patch("app.integrations.openrouter.httpx.AsyncClient") as mock_client_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_http

        await openrouter_client.generate_lesson_summary("t")

    call_kwargs = mock_http.post.call_args
    headers = call_kwargs.kwargs["headers"]
    assert headers["Authorization"] == "Bearer test-or-key"
    assert headers["HTTP-Referer"] == "https://example.com"
    assert headers["X-Title"] == "LMS"
    assert "https://openrouter.ai/api/v1" in call_kwargs.args[0]
