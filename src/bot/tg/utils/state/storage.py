from collections.abc import Mapping
from logging import getLogger
from time import monotonic
from typing import Any

from aiogram.fsm.storage.base import BaseStorage, StateType, StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from redis.exceptions import RedisError

logger = getLogger(__name__)

LOG_INTERVAL = 30.0


class FallbackStorage(BaseStorage):
    def __init__(self, primary: BaseStorage, fallback: BaseStorage | None = None):
        self.primary = primary
        self.fallback = fallback or MemoryStorage()
        self._last_log = 0.0

    def _failed(self, exc: Exception) -> None:
        now = monotonic()
        if now - self._last_log >= LOG_INTERVAL:
            self._last_log = now
            logger.error(
                "FSM storage unavailable, using in-memory state: %s: %s",
                type(exc).__name__,
                exc,
            )

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        try:
            await self.primary.set_state(key, state)
        except (RedisError, OSError) as exc:
            self._failed(exc)
            await self.fallback.set_state(key, state)

    async def get_state(self, key: StorageKey) -> str | None:
        try:
            return await self.primary.get_state(key)
        except (RedisError, OSError) as exc:
            self._failed(exc)
            return await self.fallback.get_state(key)

    async def set_data(self, key: StorageKey, data: Mapping[str, Any]) -> None:
        try:
            await self.primary.set_data(key, data)
        except (RedisError, OSError) as exc:
            self._failed(exc)
            await self.fallback.set_data(key, data)

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        try:
            return await self.primary.get_data(key)
        except (RedisError, OSError) as exc:
            self._failed(exc)
            return await self.fallback.get_data(key)

    async def close(self) -> None:
        await self.primary.close()
        await self.fallback.close()
