import asyncio
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from logging import getLogger
from typing import Any

from core.config.settings import settings
from geo.bootstrap.sources import OverpassSource, resolve_mirror_urls
from geo.dto.point import PointDTO
from geo.dto.search import ExternalState
from geo.geocoder.base import (
    GeocodedAddress,
    GeocodedPlace,
    Geocoder,
    GeocoderError,
    NearbyGeocoder,
    PlaceGeocoder,
    RateLimitedError,
)
from geo.geocoder.overpass import OverpassGeocoder
from geo.geocoder.photon import PhotonGeocoder
from geo.identity import place_words

logger = getLogger(__name__)

CacheKey = tuple[Any, ...]

MIN_QUERY_LENGTH = 3
RATE_LIMIT_PAUSE = 60.0
"""How long to stay away after a 429 that did not say how long."""
MAX_PAUSE = 900.0


class RequestBudget:
    """A token bucket: ``burst`` requests at once, then ``rate`` a second."""

    def __init__(self, rate: float, burst: int, clock: Callable[[], float]):
        self.rate = rate
        self.burst = float(max(burst, 1))
        self._clock = clock
        self._tokens = self.burst
        self._at = clock()

    def take(self) -> bool:
        if self.rate <= 0:
            return True
        now = self._clock()
        self._tokens = min(self.burst, self._tokens + (now - self._at) * self.rate)
        self._at = now
        if self._tokens < 1.0:
            return False
        self._tokens -= 1.0
        return True


@dataclass(frozen=True, slots=True)
class ExternalOutcome[T]:
    state: ExternalState
    provider: str | None = None
    items: tuple[T, ...] = ()


class ExternalSearch:
    """A geocoder behind a cache, a request budget, a concurrency cap and a breaker."""

    def __init__(
        self,
        geocoder: Geocoder,
        *,
        timeout: float = 2.0,
        ttl: float = 600.0,
        cache_size: int = 256,
        concurrency: int = 2,
        failure_threshold: int = 3,
        cooldown: float = 30.0,
        rate: float = 0.0,
        burst: int = 6,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.geocoder = geocoder
        self.timeout = timeout
        self.ttl = ttl
        self.cache_size = cache_size
        self.failure_threshold = failure_threshold
        self.cooldown = cooldown
        self.rate = rate
        self.burst = burst
        self._clock = clock
        self._budget = RequestBudget(rate, burst, clock)
        self._slots = asyncio.Semaphore(concurrency)
        self._cache: OrderedDict[CacheKey, tuple[float, tuple[Any, ...]]] = (
            OrderedDict()
        )
        self._failures = 0
        self._open_until = 0.0

    async def search(
        self, query: str, *, near: PointDTO | None, limit: int
    ) -> ExternalOutcome[GeocodedAddress]:
        key: CacheKey = (
            "search",
            " ".join(query.casefold().split()),
            (round(near.lat, 2), round(near.lon, 2)) if near else None,
            limit,
        )
        return await self._call(
            key, lambda: self.geocoder.search(query, near=near, limit=limit)
        )

    async def nearby(
        self, point: PointDTO, *, radius_km: float, limit: int
    ) -> ExternalOutcome[GeocodedAddress]:
        """Houses around a point; a geocoder that cannot list them is skipped."""
        geocoder = self.geocoder
        if not isinstance(geocoder, NearbyGeocoder):
            return ExternalOutcome("skipped", geocoder.name)
        key: CacheKey = (
            "nearby",
            round(point.lat, 2),
            round(point.lon, 2),
            radius_km,
            limit,
        )
        return await self._call(
            key, lambda: geocoder.nearby(point, radius_km=radius_km, limit=limit)
        )

    async def place(
        self, query: str, *, near: PointDTO | None
    ) -> ExternalOutcome[GeocodedPlace]:
        """The settlement a typed name stands for; none is an answer too."""
        geocoder = self.geocoder
        if not isinstance(geocoder, PlaceGeocoder):
            return ExternalOutcome("skipped", geocoder.name)
        key: CacheKey = (
            "place",
            tuple(place_words(query)),
            (round(near.lat, 1), round(near.lon, 1)) if near else None,
        )

        async def find() -> list[GeocodedPlace]:
            found = await geocoder.place(query, near=near)
            return [found] if found else []

        return await self._call(key, find)

    async def _call[T](
        self, key: CacheKey, ask: Callable[[], Awaitable[list[T]]]
    ) -> ExternalOutcome[T]:
        provider = self.geocoder.name
        cached = self._cached(key)
        if cached is not None:
            return ExternalOutcome("cached", provider, cached)
        if self._clock() < self._open_until:
            return ExternalOutcome("unavailable", provider)
        if not self._budget.take():
            return ExternalOutcome("throttled", provider)
        try:
            async with asyncio.timeout(self.timeout):
                async with self._slots:
                    found = await ask()
        except TimeoutError:
            self._failed()
            return ExternalOutcome("timeout", provider)
        except RateLimitedError as exc:
            logger.warning("%s asked to slow down: %s", provider, exc)
            pause = exc.retry_after or RATE_LIMIT_PAUSE
            self._open_until = self._clock() + min(max(pause, self.cooldown), MAX_PAUSE)
            self._failures = 0
            return ExternalOutcome("throttled", provider)
        except GeocoderError as exc:
            logger.warning("%s search failed: %s", provider, exc)
            self._failed()
            return ExternalOutcome("error", provider)
        self._failures = 0
        items = tuple(found)
        self._cache[key] = (self._clock() + self.ttl, items)
        while len(self._cache) > self.cache_size:
            self._cache.popitem(last=False)
        return ExternalOutcome("ok", provider, items)

    def _cached(self, key: CacheKey) -> tuple[Any, ...] | None:
        entry = self._cache.get(key)
        if entry is None:
            return None
        expires_at, items = entry
        if expires_at <= self._clock():
            del self._cache[key]
            return None
        self._cache.move_to_end(key)
        return items

    def _failed(self) -> None:
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._open_until = self._clock() + self.cooldown
            self._failures = 0


_shared: ExternalSearch | None = None
_shared_fallback: ExternalSearch | None = None


def shared_external_search() -> ExternalSearch | None:
    global _shared
    if not settings.GEO_EXTERNAL_SEARCH:
        return None
    if _shared is None:
        _shared = ExternalSearch(
            PhotonGeocoder(
                settings.GEO_PHOTON_URL, timeout=settings.GEO_EXTERNAL_TIMEOUT
            ),
            timeout=settings.GEO_EXTERNAL_TIMEOUT,
            rate=settings.GEO_EXTERNAL_RATE,
            burst=settings.GEO_EXTERNAL_BURST,
        )
    return _shared


def shared_fallback_search() -> ExternalSearch | None:
    """OpenStreetMap through Overpass, asked only after Photon: slow and opt-in."""
    global _shared_fallback
    if not (settings.GEO_EXTERNAL_SEARCH and settings.GEO_OVERPASS_SEARCH):
        return None
    if _shared_fallback is None:
        timeout = settings.GEO_OVERPASS_SEARCH_TIMEOUT
        urls = (
            resolve_mirror_urls(settings.GEO_OVERPASS_MIRRORS)
            if settings.GEO_OVERPASS_MIRRORS
            else None
        )
        source = OverpassSource(urls=urls, timeout=timeout, attempts=3, cooldown=10.0)
        _shared_fallback = ExternalSearch(
            OverpassGeocoder(source),
            timeout=timeout + 1.0,
            rate=settings.GEO_EXTERNAL_RATE,
            burst=settings.GEO_EXTERNAL_BURST,
        )
    return _shared_fallback
