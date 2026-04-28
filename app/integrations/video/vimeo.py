import httpx

from app.core.config import get_settings
from app.integrations.video.base import VideoMetadata


class VimeoVideoProvider:
    _BASE_API = "https://api.vimeo.com"

    def __init__(self) -> None:
        settings = get_settings()
        self._access_token = settings.vimeo_access_token.get_secret_value()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/vnd.vimeo.*+json;version=3.4",
        }

    async def get_playback_url(self, video_id: str, ttl_seconds: int = 7200) -> str:
        # Vimeo doesn't support signed HLS URLs; returns player embed URL.
        # ttl_seconds ignored — access control is managed via Vimeo privacy settings.
        return f"https://player.vimeo.com/video/{video_id}"

    async def get_metadata(self, video_id: str) -> VideoMetadata:
        url = f"{self._BASE_API}/videos/{video_id}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        thumbnail_url: str | None = None
        pictures = data.get("pictures", {})
        sizes = pictures.get("sizes", [])
        if sizes:
            thumbnail_url = sizes[-1].get("link")
        return VideoMetadata(
            video_id=video_id,
            title=data.get("name", ""),
            duration_seconds=int(data.get("duration", 0)),
            thumbnail_url=thumbnail_url,
            width=data.get("width"),
            height=data.get("height"),
        )

    async def delete(self, video_id: str) -> None:
        url = f"{self._BASE_API}/videos/{video_id}"
        async with httpx.AsyncClient() as client:
            resp = await client.delete(url, headers=self._headers())
            resp.raise_for_status()
