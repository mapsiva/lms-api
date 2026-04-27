from typing import Optional

import redis.asyncio as aioredis

redis_client: Optional[aioredis.Redis] = None


async def init_redis(redis_url: str):
    global redis_client
    redis_client = aioredis.from_url(redis_url, decode_responses=True)


async def close_redis():
    global redis_client
    if redis_client:
        await redis_client.aclose()


def get_redis() -> aioredis.Redis | None:
    return redis_client
