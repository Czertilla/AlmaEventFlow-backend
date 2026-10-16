from dataclasses import dataclass
from typing import Literal

from geo.dto.address import AddressDTO
from geo.dto.location import LocationDTO
from geo.dto.point import PointDTO

SearchKind = Literal["address", "location"]
SearchOrigin = Literal["local", "external"]
ExternalState = Literal["skipped", "ok", "cached", "timeout", "error", "unavailable"]


@dataclass(frozen=True, slots=True)
class SearchQueryDTO:
    query: str | None = None
    near: PointDTO | None = None
    limit: int = 10
    kinds: tuple[SearchKind, ...] = ("location", "address")
    city_id: int | None = None
    named_locations_only: bool = True
    external: bool = True


@dataclass(frozen=True, slots=True)
class SearchHitDTO:
    kind: SearchKind
    origin: SearchOrigin
    score: float | None
    address: AddressDTO | None = None
    location: LocationDTO | None = None


@dataclass(frozen=True, slots=True)
class ExternalStatusDTO:
    state: ExternalState
    provider: str | None = None


@dataclass(frozen=True, slots=True)
class SearchResultDTO:
    items: list[SearchHitDTO]
    external: ExternalStatusDTO
