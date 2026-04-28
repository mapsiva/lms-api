from app.integrations.video.base import VideoMetadata, VideoProvider
from app.integrations.video.bunny import BunnyVideoProvider
from app.integrations.video.mux import MuxVideoProvider
from app.integrations.video.panda import PandaVideoProvider
from app.integrations.video.vimeo import VimeoVideoProvider

_PROVIDERS: dict[str, type] = {
    "bunny": BunnyVideoProvider,
    "mux": MuxVideoProvider,
    "vimeo": VimeoVideoProvider,
    "panda": PandaVideoProvider,
}


def get_video_provider(provider_name: str) -> VideoProvider:
    cls = _PROVIDERS.get(provider_name)
    if cls is None:
        raise ValueError(f"Unknown video provider: {provider_name!r}")
    return cls()  # type: ignore[return-value]


__all__ = [
    "VideoMetadata",
    "VideoProvider",
    "BunnyVideoProvider",
    "MuxVideoProvider",
    "VimeoVideoProvider",
    "PandaVideoProvider",
    "get_video_provider",
]
