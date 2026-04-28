import hashlib
import time

import httpx

from app.core.config import get_settings
from app.integrations.video.base import VideoMetadata


class PandaVideoProvider:
    _BASE_API = "https://api-v2.pandavideo.com.br"

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.panda_api_key.get_secret_value()
        self._cdn_hostname = settings.panda_cdn_hostname

    def _headers(self) -> dict[str, str]:
        return {"Authorization": self._api_key}

    def _sign_url(self, video_id: str, ttl_seconds: int) -> str:
        expiry = int(time.time()) + ttl_seconds
        token_raw = f"{self._api_key}{video_id}{expiry}"
        token = hashlib.sha256(token_raw.encode()).hexdigest()
        return (
            f"https://{self._cdn_hostname}/{video_id}/playlist.m3u8"
            f"?token={token}&expires={expiry}"
        )

    async def get_playback_url(self, video_id: str, ttl_seconds: int = 7200) -> str:
        return self._sign_url(video_id, ttl_seconds)

    async def get_metadata(self, video_id: str) -> VideoMetadata:
        url = f"{self._BASE_API}/videos/{video_id}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        return VideoMetadata(
            video_id=video_id,
            title=data.get("title", ""),
            duration_seconds=int(data.get("length", data.get("duration", 0))),
            thumbnail_url=data.get("thumbnail"),
            width=data.get("width"),
            height=data.get("height"),
        )

    async def delete(self, video_id: str) -> None:
        url = f"{self._BASE_API}/videos/{video_id}"
        async with httpx.AsyncClient() as client:
            resp = await client.delete(url, headers=self._headers())
            resp.raise_for_status()
