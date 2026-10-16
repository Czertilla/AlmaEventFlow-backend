import asyncio
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from logging import getLogger

from core.config.settings import settings
from geo.bootstrap.sources import OverpassSource, resolve_mirror_urls
from geo.dto.point import PointDTO
from geo.dto.search import ExternalState
from geo.geocoder.base import GeocodedAddress, Geocoder, GeocoderError
from geo.geocoder.overpass import OverpassGeocoder
from geo.geocoder.photon import PhotonGeocoder

logger = getLogger(__name__)

CacheKey = tuple[str, tuple[float, float] | None, int]

MIN_QUERY_LENGTH = 3


@dataclass(frozen=True, slots=True)
class ExternalOutcome:
    state: ExternalState
    provider: str | None = None
    items: tuple[GeocodedAddress, ...] = ()


class ExternalSearch:
    """A geocoder behind a cache, a concurrency cap and a circuit breaker."""

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
        clock: Callable[[], float] = time.monotonic,
    ):
        self.geocoder = geocoder
        self.timeout = timeout
        self.ttl = ttl
        self.cache_size = cache_size
        self.failure_threshold = failure_threshold
        self.cooldown = cooldown
        self._clock = clock
        self._slots = asyncio.Semaphore(concurrency)
        self._cache: OrderedDict[
            CacheKey, tuple[float, tuple[GeocodedAddress, ...]]
        ] = OrderedDict()
        self._failures = 0
        self._open_until = 0.0

    async def search(
        self, query: str, *, near: PointDTO | None, limit: int
    ) -> ExternalOutcome:
        provider = self.geocoder.name
        key: CacheKey = (
            " ".join(query.casefold().split()),
            (round(near.lat, 2), round(near.lon, 2)) if near else None,
            limit,
        )
        cached = self._cached(key)
        if cached is not None:
            return ExternalOutcome("cached", provider, cached)
        if self._clock() < self._open_until:
            return ExternalOutcome("unavailable", provider)
        try:
            async with asyncio.timeout(self.timeout):
                async with self._slots:
                    found = await self.geocoder.search(query, near=near, limit=limit)
        except TimeoutError:
            self._failed()
            return ExternalOutcome("timeout", provider)
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

    def _cached(self, key: CacheKey) -> tuple[GeocodedAddress, ...] | None:
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
            OverpassGeocoder(source), timeout=timeout + 1.0
        )
    return _shared_fallback
