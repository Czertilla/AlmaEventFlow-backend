from dataclasses import dataclass
from uuid import UUID

from core.dto.base import FieldsSetDTOMixin


@dataclass(frozen=True, slots=True)
class OrganizationCreateDTO:
    type: str
    name: str
    acronym: str | None = None
    principal_id: UUID | None = None
    address_id: UUID | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class OrganizationPatchDTO(FieldsSetDTOMixin):
    id: UUID
    type: str | None = None
    name: str | None = None
    acronym: str | None = None
    principal_id: UUID | None = None
    address_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class OrganizationPutDTO:
    id: UUID
    type: str
    name: str
    acronym: str | None = None
    principal_id: UUID | None = None
    address_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class OrganizationDTO:
    id: UUID
    type: str
    name: str
    acronym: str | None
    principal_id: UUID | None
    address_id: UUID | None


@dataclass(frozen=True, slots=True)
class OrganizationFilterDTO:
    order_by: list[str] | None = None
    search: str | None = None
    type: str | None = None
    type__in: list[str] | None = None
