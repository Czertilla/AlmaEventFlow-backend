import datetime
from dataclasses import dataclass
from uuid import UUID

from core.dto.base import FieldsSetDTOMixin, TimestampFilterDTOMixin
from org.enum.organization import OrganizationTypeEnum


@dataclass(frozen=True, slots=True)
class OrganizationCreateDTO:
    name: str
    acronym: str | None = None
    principal_id: UUID | None = None
    address_id: UUID | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class OrganizationPatchDTO(FieldsSetDTOMixin):
    id: UUID
    name: str | None = None
    acronym: str | None = None
    principal_id: UUID | None = None
    address_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class OrganizationDTO:
    id: UUID
    type: OrganizationTypeEnum
    name: str
    acronym: str | None
    principal_id: UUID | None
    address_id: UUID | None
    created_at: datetime.datetime
    edited_at: datetime.datetime | None


@dataclass(frozen=True, slots=True)
class OrganizationFilterDTO(TimestampFilterDTOMixin):
    order_by: list[str] | None = None
    search: str | None = None
    type: OrganizationTypeEnum | None = None
    type__in: list[OrganizationTypeEnum] | None = None
    principal_id: UUID | None = None
    principal_id__isnull: bool | None = None
    address_id: UUID | None = None
    address_id__isnull: bool | None = None
