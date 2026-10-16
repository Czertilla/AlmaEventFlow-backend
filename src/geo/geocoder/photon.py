import re
from datetime import UTC, datetime
from typing import Any, cast

import aiohttp

from geo.dto.point import PointDTO
from geo.geocoder.base import GeocodedAddress, GeocoderError

_OSM_TYPES = {"N": "node", "W": "way", "R": "relation"}

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
                if response.status >= 400:
                    raise GeocoderError(f"HTTP {response.status}")
                return await response.json(content_type=None)
        except aiohttp.ClientError as exc:
            raise GeocoderError(str(exc) or type(exc).__name__) from exc
        except ValueError as exc:
            raise GeocoderError("malformed response") from exc


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
