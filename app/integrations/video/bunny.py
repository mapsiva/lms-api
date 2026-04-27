import hashlib
import time
from dataclasses import dataclass

import httpx

from app.core.config import get_settings
from app.integrations.video.base import VideoMetadata


@dataclass
class BunnyLibraryVideo:
    video_id: str
    title: str
    duration_seconds: int
    thumbnail_url: str | None


class BunnyVideoProvider:
    _BASE_API = "https://video.bunnycdn.com/library"

    def __init__(self) -> None:
        settings = get_settings()
        self._library_id = settings.bunny_stream_library_id
        self._api_key = settings.bunny_api_key.get_secret_value()
        self._cdn_hostname = settings.bunny_cdn_hostname

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
        url = f"{self._BASE_API}/{self._library_id}/videos/{video_id}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers={"AccessKey": self._api_key})
            resp.raise_for_status()
            data = resp.json()
        return VideoMetadata(
            video_id=video_id,
            title=data.get("title", ""),
            duration_seconds=int(data.get("length", 0)),
            thumbnail_url=data.get("thumbnailFileName"),
        )

    async def delete(self, video_id: str) -> None:
        url = f"{self._BASE_API}/{self._library_id}/videos/{video_id}"
        async with httpx.AsyncClient() as client:
            resp = await client.delete(url, headers={"AccessKey": self._api_key})
            resp.raise_for_status()

    async def list_library_folder(self, folder: str) -> list[BunnyLibraryVideo]:
        url = f"{self._BASE_API}/{self._library_id}/videos"
        params = {"collection": folder, "itemsPerPage": 100, "page": 1}
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url, headers={"AccessKey": self._api_key}, params=params  # type: ignore[arg-type]
            )
            resp.raise_for_status()
            data = resp.json()
        items = data.get("items", [])
        return [
            BunnyLibraryVideo(
                video_id=v["guid"],
                title=v.get("title", ""),
                duration_seconds=int(v.get("length", 0)),
                thumbnail_url=v.get("thumbnailFileName"),
            )
            for v in items
        ]
