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


class GeocoderError(Exception): ...


class Geocoder(Protocol):
    name: str

    async def search(
        self, query: str, *, near: PointDTO | None, limit: int
    ) -> list[GeocodedAddress]: ...


@runtime_checkable
class DatedGeocoder(Protocol):
    """A geocoder that knows when its data was built."""

    async def imported_at(self) -> datetime | None: ...
