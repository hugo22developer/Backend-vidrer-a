import logging

from redis.asyncio import Redis

from app.core.config import settings

log = logging.getLogger(__name__)

try:
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
except Exception:
    log.warning("Redis unavailable — caching and rate-limiting disabled")
    redis_client = None  # type: ignore[assignment]


async def close_redis() -> None:
    if redis_client is not None:
        await redis_client.aclose()

