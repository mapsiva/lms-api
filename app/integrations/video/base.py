from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class VideoMetadata:
    video_id: str
    title: str
    duration_seconds: int
    thumbnail_url: str | None = None
    width: int | None = None
    height: int | None = None


@runtime_checkable
class VideoProvider(Protocol):
    async def get_playback_url(self, video_id: str, ttl_seconds: int) -> str: ...
    async def get_metadata(self, video_id: str) -> VideoMetadata: ...
    async def delete(self, video_id: str) -> None: ...
