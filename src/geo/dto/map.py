from dataclasses import dataclass
from uuid import UUID

from core.dto.pagination import PageDTO
from geo.dto.address import AddressDTO
from geo.dto.location import LocationDTO
from geo.dto.search import SearchKind


@dataclass(frozen=True, slots=True)
class MapResultDTO:
    addresses: PageDTO[AddressDTO]
    locations: PageDTO[LocationDTO]


@dataclass(frozen=True, slots=True)
class MapQueryDTO:
    west: float
    south: float
    east: float
    north: float
    zoom: float
    radius_px: int = 64
    kinds: tuple[SearchKind, ...] = ("address", "location")
    limit: int = 1000


@dataclass(frozen=True, slots=True)
class MapEntityDTO:
    kind: SearchKind
    id: UUID
    lat: float
    lon: float
    name: str
    locality: str


@dataclass(frozen=True, slots=True)
class MapClusterDTO:
    lat: float
    lon: float
    count: int
    addresses: int
    locations: int
    west: float
    south: float
    east: float
    north: float


@dataclass(frozen=True, slots=True)
class MapViewDTO:
    features: list[MapEntityDTO | MapClusterDTO]
    matched: int
    truncated: bool

    @property
    def entities(self) -> list[MapEntityDTO]:
        return [item for item in self.features if isinstance(item, MapEntityDTO)]

    @property
    def clusters(self) -> list[MapClusterDTO]:
        return [item for item in self.features if isinstance(item, MapClusterDTO)]
