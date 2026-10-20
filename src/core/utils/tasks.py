import asyncio
from typing import Any

_background: set[asyncio.Task[Any]] = set()


def track[T: asyncio.Task[Any]](task: T) -> T:
    """Keeps a strong reference to a fire-and-forget task until it is done."""
    _background.add(task)
    task.add_done_callback(_background.discard)
    return task
