from functools import lru_cache
from typing import Annotated
from fastapi import Depends
from redis.asyncio import Redis

from core.config.settings import settings

@lru_cache
def redis_factory() -> Redis:
    return Redis.from_url(settings.REDIS_URL)

RedisDep = Annotated[Redis, Depends(redis_factory)]

redis = redis_factory()