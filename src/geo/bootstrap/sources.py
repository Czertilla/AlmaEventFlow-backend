import asyncio
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from logging import getLogger
from typing import Protocol
from uuid import NAMESPACE_URL, UUID, uuid5

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
    """Stable id *within* ``source`` -- for OSM, ``f"{type}/{id}"``."""
    street: str
    housenumber: str
    lat: float
    lon: float

    @property
    def id(self) -> UUID:
        """Deterministic, not random: re-running the bootstrap against the
        same upstream object always yields the same row, so ``upsert_many``
        (keyed on this id) naturally dedupes instead of creating a fresh
        duplicate address every run."""
        return uuid5(NAMESPACE_URL, f"{self.source}:{self.source_id}")

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


class OverpassSource:
    """Free, keyless. Respects the public instance's expectations: one
    sequential request at a time (no concurrency), a real User-Agent, and a
    generous per-request timeout since public Overpass instances can be
    slow under load."""

    URL = "https://overpass-api.de/api/interpreter"
    USER_AGENT = "AlmaEventFlow-geo-bootstrap/1.0 (+https://github.com/Czertilla/AlmaEventFlow-backend)"

    def __init__(self, *, timeout: float = 180.0, request_delay: float = 2.0):
        self.timeout = timeout
        self.request_delay = request_delay

    def _query(self, bbox: BBox) -> str:
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

    async def fetch(self, bbox: BBox) -> AsyncIterator[RawAddress]:
        await asyncio.sleep(self.request_delay)
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                self.URL,
                data={"data": self._query(bbox)},
                headers={"User-Agent": self.USER_AGENT},
            ) as response:
                response.raise_for_status()
                payload = await response.json()

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
