import time
from collections import deque
from collections.abc import Callable, Hashable


class RateLimiter:
    """At most `limit()` calls per key within a sliding `period` of seconds, kept
    in this process."""

    def __init__(
        self,
        limit: Callable[[], int],
        period: float = 3600.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._limit = limit
        self._period = period
        self._clock = clock
        self._calls: dict[Hashable, deque[float]] = {}

    def allow(self, key: Hashable) -> float | None:
        """Counts a call; `None` when it is allowed, else the seconds to wait."""
        now = self._clock()
        calls = self._calls.setdefault(key, deque())
        while calls and calls[0] <= now - self._period:
            calls.popleft()
        if len(calls) >= max(self._limit(), 0):
            return calls[0] + self._period - now if calls else self._period
        calls.append(now)
        return None

    def reset(self) -> None:
        self._calls.clear()
