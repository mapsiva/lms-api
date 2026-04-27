import hashlib
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.video.base import VideoMetadata, VideoProvider
from app.integrations.video.bunny import BunnyLibraryVideo, BunnyVideoProvider


@pytest.fixture
def bunny(monkeypatch):
    monkeypatch.setenv("BUNNY_STREAM_LIBRARY_ID", "lib123")
    monkeypatch.setenv("BUNNY_API_KEY", "secret-api-key")
    monkeypatch.setenv("BUNNY_CDN_HOSTNAME", "cdn.example.b-cdn.net")
    with patch("app.integrations.video.bunny.get_settings") as mock_settings:
        settings = MagicMock()
        settings.bunny_stream_library_id = "lib123"
        settings.bunny_api_key.get_secret_value.return_value = "secret-api-key"
        settings.bunny_cdn_hostname = "cdn.example.b-cdn.net"
        mock_settings.return_value = settings
        yield BunnyVideoProvider()


def test_video_provider_protocol():
    assert issubclass(BunnyVideoProvider, VideoProvider)


def test_sign_url_deterministic(bunny):
    video_id = "abc-video-123"
    ttl = 3600
    fixed_time = 1700000000

    with patch("app.integrations.video.bunny.time.time", return_value=fixed_time):
        url1 = bunny._sign_url(video_id, ttl)
        url2 = bunny._sign_url(video_id, ttl)

    assert url1 == url2
    assert "token=" in url1
    assert f"expires={fixed_time + ttl}" in url1
    assert "cdn.example.b-cdn.net" in url1
    assert video_id in url1


def test_sign_url_contains_correct_token(bunny):
    video_id = "test-vid"
    ttl = 7200
    fixed_time = 1700000000
    expiry = fixed_time + ttl
    expected_token = hashlib.sha256(
        f"secret-api-key{video_id}{expiry}".encode()
    ).hexdigest()

    with patch("app.integrations.video.bunny.time.time", return_value=fixed_time):
        url = bunny._sign_url(video_id, ttl)

    assert f"token={expected_token}" in url


def test_sign_url_never_exposes_raw_url(bunny):
    with patch("app.integrations.video.bunny.time.time", return_value=1700000000):
        url = bunny._sign_url("vid123", 3600)
    assert "token=" in url
    assert "expires=" in url


def test_sign_url_different_videos_different_tokens(bunny):
    fixed_time = 1700000000
    with patch("app.integrations.video.bunny.time.time", return_value=fixed_time):
        url1 = bunny._sign_url("video-A", 3600)
        url2 = bunny._sign_url("video-B", 3600)
    assert url1 != url2


@pytest.mark.asyncio
async def test_get_playback_url_returns_signed(bunny):
    with patch("app.integrations.video.bunny.time.time", return_value=1700000000):
        url = await bunny.get_playback_url("vid-xyz", ttl_seconds=3600)
    assert "token=" in url
    assert "expires=1700003600" in url


@pytest.mark.asyncio
async def test_list_library_folder(bunny):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "items": [
            {"guid": "v1", "title": "Intro", "length": 120, "thumbnailFileName": "thumb.jpg"},
            {"guid": "v2", "title": "Lesson 2", "length": 300, "thumbnailFileName": None},
        ]
    }
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("app.integrations.video.bunny.httpx.AsyncClient", return_value=mock_client):
        result = await bunny.list_library_folder("my-folder")

    assert len(result) == 2
    assert result[0].video_id == "v1"
    assert result[0].title == "Intro"
    assert result[0].duration_seconds == 120
    assert result[0].thumbnail_url == "thumb.jpg"
    assert result[1].video_id == "v2"
    assert result[1].thumbnail_url is None


def test_video_metadata_dataclass():
    meta = VideoMetadata(
        video_id="v1",
        title="Test",
        duration_seconds=120,
        thumbnail_url="http://example.com/thumb.jpg",
    )
    assert meta.video_id == "v1"
    assert meta.duration_seconds == 120
