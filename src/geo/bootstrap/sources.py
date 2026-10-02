import asyncio
from collections.abc import AsyncIterator, Iterator, Sequence
from dataclasses import dataclass
from logging import getLogger
from typing import Protocol
from urllib.parse import urlsplit

import aiohttp

logger = getLogger(__name__)

BBox = tuple[float, float, float, float]
"""(min_lat, min_lon, max_lat, max_lon)."""


@dataclass(frozen=True)
class RawAddress:
    source: str
    """Where this row came from, e.g. ``"osm"`` -- lets a future second
    source (DaData, GAR) coexist without id collisions."""
    source_id: str
    """Stable id *within* ``source`` -- for OSM, ``f"{type}/{id}"``. Not used
    to key the stored row (see ``run._address_id``): the same real-world
    address can end up under a different upstream element id between
    reimports (a redrawn way, a node retagged to a way, ...)."""
    street: str
    housenumber: str
    lat: float
    lon: float

    @property
    def name(self) -> str:
        return f"{self.street}, {self.housenumber}"


class AddressSource(Protocol):
    async def fetch(self, bbox: BBox) -> AsyncIterator[RawAddress]: ...


def chunk_bbox(bbox: BBox, *, grid: int) -> Iterator[BBox]:
    """Splits a bbox into a ``grid`` x ``grid`` cell grid -- not real
    administrative district boundaries (Moscow's aren't hardcoded here),
    just a way to keep any one Overpass request small and let a failure
    partway through resume from the next cell instead of restarting the
    whole city."""
    min_lat, min_lon, max_lat, max_lon = bbox
    lat_step = (max_lat - min_lat) / grid
    lon_step = (max_lon - min_lon) / grid
    for row in range(grid):
        for col in range(grid):
            yield (
                min_lat + row * lat_step,
                min_lon + col * lon_step,
                min_lat + (row + 1) * lat_step,
                min_lon + (col + 1) * lon_step,
            )


MIRRORS: dict[str, str] = {
    "osm-fr": "https://overpass.openstreetmap.fr/api/interpreter",
    "lz4": "https://lz4.overpass-api.de/api/interpreter",
    "z": "https://z.overpass-api.de/api/interpreter",
    "main": "https://overpass-api.de/api/interpreter",
    "mail-ru": "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "kumi": "https://overpass.kumi.systems/api/interpreter",
}

DEFAULT_MIRRORS = ("osm-fr", "lz4", "z", "main", "mail-ru")

_RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})


def resolve_mirror_urls(servers: str) -> list[str]:
    """Comma-separated mirror names (looked up in ``MIRRORS``) or full URLs,
    tried in the given order. Shared by the CLI's ``--servers`` flag and
    ``settings.GEO_OVERPASS_MIRRORS`` so both configure the same pool the
    same way."""
    return [
        MIRRORS.get(name.strip(), name.strip())
        for name in servers.split(",")
        if name.strip()
    ]


class OverpassError(Exception): ...


class _Retryable(Exception): ...


_SETTLEMENT_PREFIXES = (
    "городской округ ",
    "городское поселение ",
    "сельское поселение ",
)


def _strip_settlement_prefix(name: str) -> str:
    for prefix in _SETTLEMENT_PREFIXES:
        if name.startswith(prefix):
            return name[len(prefix) :]
    return name


def pick_administrative_names(levels: dict[int, str]) -> tuple[str, str, str]:
    """Picks (country, region, city) names out of an ``admin_level -> name``
    map from ``OverpassSource.reverse_geocode`` -- never a placeholder: a
    country with no finer OSM subdivision at this point reuses its own name
    for region and city rather than leaving them blank or fake.

    ``admin_level`` isn't a fixed universal scale -- what it means past 2
    (country) varies by country, and blindly taking "the next level up" or
    "the deepest level available" picks up things that aren't a region or a
    city at all. Verified against real Overpass data for three different
    Russian structures:
    - a federal subject organized as one urban okrug (Tatarstan/Kazan):
      country(2) -> [federal district(3), skipped] -> region(4) ->
      city(6, "городской округ Казань") -> [district(9), too fine, skipped].
    - a federal subject with a two-tier municipal split (Yaroslavl oblast/
      Rostov Veliky): region(4) -> a level-6 "municipal okrug" that is only
      the *district* around the town, not the town -- the actual settlement
      is one level deeper (8, "городское поселение Ростов"). Picking level 6
      unconditionally here would resolve "city" to the district's name.
    - a federal city (Saint Petersburg) has no level-6 entry at all, only
      sub-city boroughs (5, 8) -- picking the deepest level available would
      wrongly resolve "city" to a borough; falls back to the region's own
      name (region and city are the same real place here).

    A level-8 settlement name is only trusted once a level-6 entry confirms
    the deeper levels are genuine district->settlement drill-down and not
    just a federal city's internal boroughs. The common
    "городской округ"/"...поселение " administrative prefix is stripped from
    whichever name wins, since it names the administrative unit, not the
    place, e.g. "городской округ Казань" -> "Казань"."""
    if not levels:
        raise OverpassError("no administrative boundary data for this point")
    country_level = 2 if 2 in levels else min(levels)
    country = levels[country_level]

    region = levels[4] if 4 in levels and country_level != 4 else country

    city = levels.get(8, levels[6]) if 6 in levels else region

    return country, region, _strip_settlement_prefix(city)


class OverpassSource:
    """Free, keyless, and every public instance is flaky on its own, so
    requests are spread over a pool of mirrors: each mirror serves one
    request at a time (the public instances' usage policy), a failing
    mirror sits out a growing cooldown, and the request moves on to the
    next one instead of waiting on a dead server."""

    USER_AGENT = "AlmaEventFlow-geo-bootstrap/1.0 (+https://github.com/Czertilla/AlmaEventFlow-backend)"

    def __init__(
        self,
        *,
        urls: Sequence[str] | None = None,
        timeout: float = 60.0,
        attempts: int = 6,
        cooldown: float = 30.0,
        request_delay: float = 0.0,
    ):
        self.urls = tuple(urls or (MIRRORS[name] for name in DEFAULT_MIRRORS))
        self.timeout = timeout
        self.attempts = attempts
        self.cooldown = cooldown
        self.request_delay = request_delay
        self._idle: asyncio.Queue[str] = asyncio.Queue()
        self._strikes: dict[str, int] = dict.fromkeys(self.urls, 0)
        for url in self.urls:
            self._idle.put_nowait(url)

    def _address_query(self, bbox: BBox) -> str:
        min_lat, min_lon, max_lat, max_lon = bbox
        box = f"{min_lat},{min_lon},{max_lat},{max_lon}"
        return f"""
        [out:json][timeout:{int(self.timeout)}];
        (
          node["addr:housenumber"]["addr:street"]({box});
          way["addr:housenumber"]["addr:street"]({box});
        );
        out center;
        """

    def _is_in_query(self, lat: float, lon: float) -> str:
        return f"""
        [out:json][timeout:{int(self.timeout)}];
        is_in({lat},{lon})->.a;
        area.a[boundary=administrative][admin_level];
        out tags;
        """

    async def _request(self, url: str, query: str) -> dict:
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            async with session.post(
                url,
                data={"data": query},
                headers={"User-Agent": self.USER_AGENT},
            ) as response:
                if response.status in _RETRYABLE_STATUSES:
                    raise _Retryable(f"HTTP {response.status}")
                if response.status >= 400:
                    raise OverpassError(f"HTTP {response.status} from {url}")
                payload = await response.json(content_type=None)
        remark = payload.get("remark") or ""
        if "runtime error" in remark:
            raise _Retryable(remark)
        return payload

    async def _post(self, query: str) -> dict:
        last_error: BaseException | None = None
        for attempt in range(1, self.attempts + 1):
            url = await self._idle.get()
            try:
                payload = await self._request(url, query)
            except (TimeoutError, _Retryable, aiohttp.ClientError) as exc:
                last_error = exc
                self._strikes[url] += 1
                delay = min(self.cooldown * self._strikes[url], 300.0)
                asyncio.get_running_loop().call_later(delay, self._idle.put_nowait, url)
                logger.info(
                    "%s failed (%s), attempt %d/%d",
                    urlsplit(url).hostname,
                    exc or type(exc).__name__,
                    attempt,
                    self.attempts,
                )
                continue
            except BaseException:
                self._idle.put_nowait(url)
                raise
            self._strikes[url] = 0
            self._idle.put_nowait(url)
            return payload
        raise OverpassError(f"no mirror answered, last error: {last_error!r}")

    async def reverse_geocode(self, lat: float, lon: float) -> dict[int, str]:
        """Administrative boundaries containing ``(lat, lon)``, keyed by
        ``admin_level`` (2=country, then progressively finer subdivisions --
        the exact meaning of each level past 2 varies by country). Free via
        Overpass's own ``is_in`` -- no separate geocoding service needed."""
        payload = await self._post(self._is_in_query(lat, lon))
        levels: dict[int, str] = {}
        for element in payload.get("elements", []):
            tags = element.get("tags", {})
            name = tags.get("name")
            level = tags.get("admin_level")
            if not name or level is None:
                continue
            try:
                levels[int(level)] = name
            except ValueError:
                continue
        return levels

    async def fetch(self, bbox: BBox) -> AsyncIterator[RawAddress]:
        if self.request_delay:
            await asyncio.sleep(self.request_delay)
        payload = await self._post(self._address_query(bbox))

        for element in payload.get("elements", []):
            tags = element.get("tags", {})
            street = tags.get("addr:street")
            housenumber = tags.get("addr:housenumber")
            if not street or not housenumber:
                continue

            if element["type"] == "node":
                lat, lon = element.get("lat"), element.get("lon")
            else:
                center = element.get("center") or {}
                lat, lon = center.get("lat"), center.get("lon")
            if lat is None or lon is None:
                continue

            yield RawAddress(
                source="osm",
                source_id=f"{element['type']}/{element['id']}",
                street=street,
                housenumber=housenumber,
                lat=lat,
                lon=lon,
            )
