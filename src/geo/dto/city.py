from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CityCascadeCreateDTO:
    name: str
    region: str
    country: str


@dataclass(frozen=True, slots=True)
class CityDTO:
    id: int
    region_id: int
    name: str
    acronym: str | None = None


@dataclass(frozen=True, slots=True)
class CityFilterDTO:
    order_by: list[str] | None = None
    search: str | None = None
    region_id: int | None = None
    region_id__in: list[int] | None = None
