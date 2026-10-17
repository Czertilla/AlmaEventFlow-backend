import re
from datetime import UTC, datetime
from typing import Any, cast

import aiohttp

from geo.dto.point import PointDTO
from geo.geocoder.base import (
    GeocodedAddress,
    GeocodedPlace,
    GeocoderError,
    RateLimitedError,
)
from geo.identity import (
    STREET_TYPE_WORDS,
    address_key,
    meters_between,
    place_words,
    starts_like,
)

_OSM_TYPES = {"N": "node", "W": "way", "R": "relation"}
PLACE_CANDIDATES = 5
NEARBY_OVERFETCH = 6
STREET_NEAR_M = 30_000.0
MAX_NEARBY = 50
HTTP_TOO_MANY_REQUESTS = 429
_EXTENT_SIZE = 4

_ADMINISTRATIVE_UNIT = re.compile(
    r"\b(городск|сельск|муниципальн)\w+ (поселение|округ|район)\b"
    r"|^(поселение|округ) ",
    re.IGNORECASE,
)


class PhotonGeocoder:
    """Photon, houses only: an address row needs a street and a house number."""

    name = "photon"
    USER_AGENT = (
        "AlmaEventFlow-geo/1.0 (+https://github.com/Czertilla/AlmaEventFlow-backend)"
    )

    def __init__(self, url: str, *, timeout: float = 2.0):
        self.url = url.rstrip("/")
        self.timeout = timeout

    async def search(
        self, query: str, *, near: PointDTO | None, limit: int
    ) -> list[GeocodedAddress]:
        params: dict[str, str] = {"q": query, "layer": "house", "limit": str(limit)}
        if near is not None:
            params["lat"] = str(near.lat)
            params["lon"] = str(near.lon)
        return parse_features(await self._get("/api", params))

    async def imported_at(self) -> datetime | None:
        return parse_import_date(await self._get("/status", {}))

    async def place(
        self, query: str, *, near: PointDTO | None
    ) -> GeocodedPlace | None:
        """The settlement the words name, unless they name a street near ``near``."""
        if near is not None and await self._names_street_near(query, near):
            return None
        params = {"q": query, "layer": "city", "limit": str(PLACE_CANDIDATES)}
        return pick_place(query, await self._get("/api", params))

    async def _names_street_near(self, query: str, near: PointDTO) -> bool:
        params = {
            "q": query,
            "layer": "street",
            "lat": str(near.lat),
            "lon": str(near.lon),
            "limit": str(PLACE_CANDIDATES),
        }
        return names_street_near(query, near, await self._get("/api", params))

    async def nearby(
        self, point: PointDTO, *, radius_km: float, limit: int
    ) -> list[GeocodedAddress]:
        params = {
            "lat": str(point.lat),
            "lon": str(point.lon),
            "layer": "house",
            "radius": str(radius_km),
            "limit": str(min(limit * NEARBY_OVERFETCH, MAX_NEARBY)),
        }
        found = parse_features(await self._get("/reverse", params))
        distinct: dict[tuple[str, str], GeocodedAddress] = {}
        for item in found:
            distinct.setdefault(address_key(item.street, item.housenumber), item)
        return list(distinct.values())[:limit]

    async def _get(self, path: str, params: dict[str, str]) -> Any:
        try:
            async with (
                aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.timeout), trust_env=True
                ) as session,
                session.get(
                    f"{self.url}{path}",
                    params=params,
                    headers={"User-Agent": self.USER_AGENT},
                ) as response,
            ):
                if response.status == HTTP_TOO_MANY_REQUESTS:
                    raise RateLimitedError(
                        "HTTP 429", retry_after_of(response.headers.get("Retry-After"))
                    )
                if response.status >= 400:
                    raise GeocoderError(f"HTTP {response.status}")
                return await response.json(content_type=None)
        except aiohttp.ClientError as exc:
            raise GeocoderError(str(exc) or type(exc).__name__) from exc
        except ValueError as exc:
            raise GeocoderError("malformed response") from exc


def retry_after_of(header: str | None) -> float | None:
    """Seconds from a ``Retry-After`` header; a date or nonsense is no answer."""
    try:
        seconds = float(header) if header is not None else 0.0
    except ValueError:
        return None
    return seconds if seconds > 0 else None


def names_street_near(query: str, near: PointDTO, payload: Any) -> bool:
    """A street whose name starts with the words lies within ``STREET_NEAR_M``."""
    features: Any = (
        cast("dict[str, Any]", payload).get("features")
        if isinstance(payload, dict)
        else None
    )
    if not isinstance(features, list):
        raise GeocoderError("malformed response")
    wanted = [word for word in place_words(query) if word not in STREET_TYPE_WORDS]
    for feature in cast("list[Any]", features):
        if not isinstance(feature, dict):
            continue
        body = cast("dict[str, Any]", feature)
        properties: dict[str, Any] = body.get("properties") or {}
        geometry: dict[str, Any] = body.get("geometry") or {}
        coordinates: list[Any] = geometry.get("coordinates") or []
        name = _text(properties, "name")
        if not name or len(coordinates) < 2:
            continue
        words = [word for word in place_words(name) if word not in STREET_TYPE_WORDS]
        lat, lon = float(coordinates[1]), float(coordinates[0])
        if starts_like(wanted, words) and (
            meters_between(near.lat, near.lon, lat, lon) <= STREET_NEAR_M
        ):
            return True
    return False


def pick_place(query: str, payload: Any) -> GeocodedPlace | None:
    """The first settlement whose name starts with the typed words.

    A street, a shop or a district that happens to share a word is not one.
    """
    features: Any = (
        cast("dict[str, Any]", payload).get("features")
        if isinstance(payload, dict)
        else None
    )
    if not isinstance(features, list):
        raise GeocoderError("malformed response")
    wanted = place_words(query)
    for feature in cast("list[Any]", features):
        place = _place(feature)
        if place is not None and starts_like(wanted, place_words(place.name)):
            return place
    return None


def _place(feature: Any) -> GeocodedPlace | None:
    if not isinstance(feature, dict):
        return None
    body = cast("dict[str, Any]", feature)
    properties: dict[str, Any] = body.get("properties") or {}
    geometry: dict[str, Any] = body.get("geometry") or {}
    coordinates: list[Any] = geometry.get("coordinates") or []
    name = _text(properties, "name")
    if properties.get("osm_key") != "place" or not name or len(coordinates) < 2:
        return None
    extent: Any = properties.get("extent")
    bbox: tuple[float, float, float, float] | None = None
    if isinstance(extent, list) and len(cast("list[Any]", extent)) == _EXTENT_SIZE:
        west, north, east, south = (float(value) for value in cast("list[Any]", extent))
        bbox = (west, south, east, north)
    return GeocodedPlace(
        name=name,
        region=_text(properties, "state"),
        country=_text(properties, "country"),
        lat=float(coordinates[1]),
        lon=float(coordinates[0]),
        bbox=bbox,
    )


def parse_import_date(payload: Any) -> datetime | None:
    value: Any = (
        cast("dict[str, Any]", payload).get("import_date")
        if isinstance(payload, dict)
        else None
    )
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def parse_features(payload: Any) -> list[GeocodedAddress]:
    features: Any = (
        cast("dict[str, Any]", payload).get("features")
        if isinstance(payload, dict)
        else None
    )
    if not isinstance(features, list):
        raise GeocoderError("malformed response")
    found: list[GeocodedAddress] = []
    for feature in cast("list[Any]", features):
        address = _house(feature)
        if address is not None:
            found.append(address)
    return found


def _text(properties: dict[str, Any], key: str) -> str:
    value = properties.get(key)
    return value.strip() if isinstance(value, str) else ""


def _house(feature: Any) -> GeocodedAddress | None:
    if not isinstance(feature, dict):
        return None
    body = cast("dict[str, Any]", feature)
    properties: dict[str, Any] = body.get("properties") or {}
    geometry: dict[str, Any] = body.get("geometry") or {}
    coordinates: list[Any] = geometry.get("coordinates") or []
    street = _text(properties, "street")
    housenumber = _text(properties, "housenumber")
    city = _text(properties, "city")
    country = _text(properties, "country")
    osm_type = _OSM_TYPES.get(_text(properties, "osm_type"))
    osm_id: Any = properties.get("osm_id")
    if not (street and housenumber and city and country and osm_type and osm_id):
        return None
    if len(coordinates) < 2 or _ADMINISTRATIVE_UNIT.search(city):
        return None
    return GeocodedAddress(
        source_id=f"{osm_type}/{osm_id}",
        street=street,
        housenumber=housenumber,
        lat=float(coordinates[1]),
        lon=float(coordinates[0]),
        city=city,
        region=_text(properties, "state") or country,
        country=country,
    )
