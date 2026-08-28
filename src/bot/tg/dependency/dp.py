from functools import lru_cache
from typing import Annotated

from aiogram import Dispatcher
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from fastapi import Depends

from core.dependencies.redis import RedisDep, redis


@lru_cache
def memory_storage_factory() -> MemoryStorage:
    return MemoryStorage()


def redis_storage_factory(redis: RedisDep) -> RedisStorage:
    return RedisStorage(redis=redis)


@lru_cache
def init_dp_factory() -> Dispatcher:
    dp = Dispatcher()
    return dp


@lru_cache
def dp_factory(
    storage: BaseStorage = Depends(redis_storage_factory),
    dp: Dispatcher = Depends(init_dp_factory),
) -> Dispatcher:
    dp.fsm.storage = storage

    return dp


DpDep = Annotated[Dispatcher, Depends(dp_factory)]

dp = dp_factory(RedisStorage(redis), init_dp_factory())
