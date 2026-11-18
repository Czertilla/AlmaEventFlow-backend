from typing import Any

import pytest
from aiogram.fsm.storage.base import BaseStorage, StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from redis.exceptions import AuthenticationError

from bot.tg.utils.state.storage import FallbackStorage

KEY = StorageKey(bot_id=1, chat_id=2, user_id=3)


class BrokenStorage(BaseStorage):
    async def set_state(self, key: StorageKey, state: Any = None) -> None:
        raise AuthenticationError("HELLO must be called")

    async def get_state(self, key: StorageKey) -> str | None:
        raise AuthenticationError("HELLO must be called")

    async def set_data(self, key: StorageKey, data: Any) -> None:
        raise ConnectionResetError("lost")

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        raise ConnectionResetError("lost")

    async def close(self) -> None:
        return None


@pytest.mark.asyncio
async def test_broken_redis_falls_back_to_memory() -> None:
    storage = FallbackStorage(BrokenStorage())
    assert await storage.get_state(KEY) is None
    await storage.set_state(KEY, "Menu:main")
    await storage.set_data(KEY, {"a": 1})
    assert await storage.get_state(KEY) == "Menu:main"
    assert await storage.get_data(KEY) == {"a": 1}


@pytest.mark.asyncio
async def test_healthy_primary_is_used() -> None:
    primary = MemoryStorage()
    fallback = MemoryStorage()
    storage = FallbackStorage(primary, fallback)
    await storage.set_state(KEY, "Menu:main")
    assert await primary.get_state(KEY) == "Menu:main"
    assert await fallback.get_state(KEY) is None
