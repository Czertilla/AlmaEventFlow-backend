from dataclasses import dataclass

from core.dto.base import FieldsSetDTOMixin


@dataclass(frozen=True, slots=True)
class DietCreateDTO:
    name: str
    description: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class DietPatchDTO(FieldsSetDTOMixin):
    id: int
    name: str | None = None
    description: str | None = None


@dataclass(frozen=True, slots=True)
class DietPutDTO:
    id: int
    name: str
    description: str | None = None


@dataclass(frozen=True, slots=True)
class DietDTO:
    id: int
    name: str
    description: str | None


@dataclass(frozen=True, slots=True)
class DietFilterDTO:
    order_by: list[str] | None = None
    search: str | None = None
