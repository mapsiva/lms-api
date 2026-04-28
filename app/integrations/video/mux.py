import base64
import time

import httpx
from jose import jwt  # type: ignore[import-untyped]

from app.core.config import get_settings
from app.integrations.video.base import VideoMetadata


class MuxVideoProvider:
    _BASE_API = "https://api.mux.com"

    def __init__(self) -> None:
        settings = get_settings()
        self._token_id = settings.mux_token_id
        self._token_secret = settings.mux_token_secret.get_secret_value()
        self._signing_key_id = settings.mux_signing_key_id
        self._signing_key_secret = settings.mux_signing_key_secret.get_secret_value()

    def _auth(self) -> tuple[str, str]:
        return (self._token_id, self._token_secret)

    def _sign_playback_token(self, playback_id: str, ttl_seconds: int) -> str:
        key_bytes = base64.b64decode(self._signing_key_secret)
        now = int(time.time())
        return jwt.encode(
            {"sub": playback_id, "aud": "v", "exp": now + ttl_seconds, "kid": self._signing_key_id},
            key_bytes,
            algorithm="RS256",
        )

    async def get_playback_url(self, video_id: str, ttl_seconds: int = 7200) -> str:
        # video_id = Mux asset_id; fetch associated playback_id
        url = f"{self._BASE_API}/video/v1/assets/{video_id}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, auth=self._auth())
            resp.raise_for_status()
            data = resp.json()["data"]
        playback_ids = data.get("playback_ids", [])
        playback_id = playback_ids[0]["id"] if playback_ids else video_id
        token = self._sign_playback_token(playback_id, ttl_seconds)
        return f"https://stream.mux.com/{playback_id}.m3u8?token={token}"

    async def get_metadata(self, video_id: str) -> VideoMetadata:
        url = f"{self._BASE_API}/video/v1/assets/{video_id}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, auth=self._auth())
            resp.raise_for_status()
            data = resp.json()["data"]
        tracks = data.get("tracks", [])
        video_track: dict[str, int | None] = next((t for t in tracks if t.get("type") == "video"), {})
        return VideoMetadata(
            video_id=video_id,
            title=data.get("id", ""),
            duration_seconds=int(data.get("duration", 0)),
            width=video_track.get("max_width"),
            height=video_track.get("max_height"),
        )

    async def delete(self, video_id: str) -> None:
        url = f"{self._BASE_API}/video/v1/assets/{video_id}"
        async with httpx.AsyncClient() as client:
            resp = await client.delete(url, auth=self._auth())
            resp.raise_for_status()
