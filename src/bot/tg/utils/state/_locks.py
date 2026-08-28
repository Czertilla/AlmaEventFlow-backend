"""
Module for storing global locks.
This module should be imported only once to prevent overwriting global data.
"""
from asyncio import Lock
from uuid import UUID

# Global locks pool for MemoryStorage
_memory_locks: dict[str, Lock] = {}
_state_debounces: dict[str, UUID] = {}
