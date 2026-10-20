"""
Utilities for managing FSM state locks.
"""

from asyncio import Lock
from typing import Any
from uuid import UUID, uuid4

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.redis import RedisStorage

from ._locks import memory_locks, state_debounces


def get_state_lock(state: FSMContext) -> Any:
    """
    Get lock for FSM state.

    Args:
        state: FSM context

    Returns:
        Redis lock for RedisStorage or asyncio Lock for other storage types
    """
    storage_key = str(state.key)

    if storage_key not in memory_locks:
        memory_locks[storage_key] = Lock()

    return memory_locks[storage_key]


def _get_debounce_key(state: FSMContext) -> str:
    storage = state.storage
    if isinstance(storage, RedisStorage):
        return storage.key_builder.build(state.key, "data")
    else:
        return str(state.key)


def set_state_debounce(state: FSMContext) -> UUID:
    state_debounces[_get_debounce_key(state)] = (result := uuid4())
    return result


def get_state_debounce(state: FSMContext) -> UUID | None:
    return state_debounces.get(_get_debounce_key(state), None)


def clear_state_debounce(state: FSMContext) -> None:
    state_debounces.pop(_get_debounce_key(state), None)
