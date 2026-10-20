"""
Module for storing global locks.
This module should be imported only once to prevent overwriting global data.
"""
from asyncio import Lock
from uuid import UUID

memory_locks: dict[str, Lock] = {}
state_debounces: dict[str, UUID] = {}
