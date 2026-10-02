from dataclasses import dataclass
from uuid import UUID

from core.dto.base import FieldsSetDTOMixin


@dataclass(frozen=True, slots=True)
class UniversityCreateDTO:
    name: str
    acronym: str | None = None
    principal_id: UUID | None = None
    address_id: UUID | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class UniversityPatchDTO(FieldsSetDTOMixin):
    id: UUID
    name: str | None = None
    acronym: str | None = None
    principal_id: UUID | None = None
    address_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class UniversityPutDTO:
    id: UUID
    name: str
    acronym: str | None = None
    principal_id: UUID | None = None
    address_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class UniversityDTO:
    id: UUID
    name: str
    acronym: str | None
    principal_id: UUID | None
    address_id: UUID | None
    type: str


@dataclass(frozen=True, slots=True)
class UniversityFilterDTO:
    order_by: list[str] | None = None
    search: str | None = None
