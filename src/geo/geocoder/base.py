from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

from geo.dto.point import PointDTO


@dataclass(frozen=True, slots=True)
class GeocodedAddress:
    source_id: str
    street: str
    housenumber: str
    lat: float
    lon: float
    city: str
    region: str
    country: str
    source: str = "photon"
    """The stored row's source: an OpenStreetMap element is ``osm`` however found."""

    @property
    def name(self) -> str:
        return f"{self.street}, {self.housenumber}"

    @property
    def placed(self) -> bool:
        return bool(self.city and self.country)


@dataclass(frozen=True, slots=True)
class GeocodedPlace:
    """A settlement: its name, where it lies and the box around it."""

    name: str
    region: str
    country: str
    lat: float
    lon: float
    bbox: tuple[float, float, float, float] | None = None
    """(west, south, east, north)."""


class GeocoderError(Exception): ...


class RateLimitedError(GeocoderError):
    """The service answered 429: ``retry_after`` is the pause it asked for."""

    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class Geocoder(Protocol):
    name: str

    async def search(
        self, query: str, *, near: PointDTO | None, limit: int
    ) -> list[GeocodedAddress]: ...


@runtime_checkable
class DatedGeocoder(Protocol):
    """A geocoder that knows when its data was built."""

    async def imported_at(self) -> datetime | None: ...


@runtime_checkable
class PlaceGeocoder(Protocol):
    """A geocoder that can tell where a settlement named by the user is."""

    async def place(
        self, query: str, *, near: PointDTO | None
    ) -> GeocodedPlace | None: ...


@runtime_checkable
class NearbyGeocoder(Protocol):
    """A geocoder that lists the houses around a point, nearest first."""

    async def nearby(
        self, point: PointDTO, *, radius_km: float, limit: int
    ) -> list[GeocodedAddress]: ...
