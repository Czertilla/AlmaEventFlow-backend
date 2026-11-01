import time
from collections import OrderedDict
from collections.abc import Callable
from uuid import UUID

from core.config.settings import settings

CacheKey = tuple[UUID, int]


def wipe(key: bytearray) -> None:
    key[:] = bytes(len(key))


class DekCache:
    """Unwrapped data keys by `(person_id, dek_version)`: at most `max_size`, each
    for `ttl_seconds`. A key that leaves the cache is overwritten with zeros
    (best effort: copies made by the cipher library are out of reach)."""

    def __init__(
        self,
        max_size: int,
        ttl_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max = max(max_size, 0)
        self._ttl = ttl_seconds
        self._clock = clock
        self._items: OrderedDict[CacheKey, tuple[float, bytearray]] = OrderedDict()

    @property
    def enabled(self) -> bool:
        return self._max > 0 and self._ttl > 0

    def __len__(self) -> int:
        return len(self._items)

    def get(self, key: CacheKey) -> bytearray | None:
        item = self._items.get(key)
        if item is None:
            return None
        expires, dek = item
        if self._clock() >= expires:
            self._evict(key)
            return None
        self._items.move_to_end(key)
        return bytearray(dek)

    def put(self, key: CacheKey, dek: bytearray) -> None:
        if not self.enabled:
            return
        if key in self._items:
            self._evict(key)
        self._items[key] = (self._clock() + self._ttl, bytearray(dek))
        while len(self._items) > self._max:
            self._evict(next(iter(self._items)))

    def drop(self, person_id: UUID) -> None:
        for key in [key for key in self._items if key[0] == person_id]:
            self._evict(key)

    def clear(self) -> None:
        for key in list(self._items):
            self._evict(key)

    def _evict(self, key: CacheKey) -> None:
        _, dek = self._items.pop(key)
        wipe(dek)


_cache: DekCache | None = None


def dek_cache() -> DekCache:
    global _cache
    if _cache is None:
        _cache = DekCache(settings.DEK_CACHE_MAX, settings.DEK_CACHE_TTL_SEC)
    return _cache


def install_dek_cache(cache: DekCache | None) -> None:
    global _cache
    _cache = cache
