import datetime
from dataclasses import dataclass
from uuid import UUID

from core.dto.base import FieldsSetDTOMixin, TimestampFilterDTOMixin


@dataclass(frozen=True, slots=True)
class FacultyCreateDTO:
    name: str
    acronym: str | None = None
    principal_id: UUID | None = None
    address_id: UUID | None = None
    university_id: UUID | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class FacultyPatchDTO(FieldsSetDTOMixin):
    id: UUID
    name: str | None = None
    acronym: str | None = None
    principal_id: UUID | None = None
    address_id: UUID | None = None
    university_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class FacultyPutDTO:
    id: UUID
    name: str
    acronym: str | None = None
    principal_id: UUID | None = None
    address_id: UUID | None = None
    university_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class FacultyDTO:
    id: UUID
    name: str
    acronym: str | None
    principal_id: UUID | None
    address_id: UUID | None
    university_id: UUID | None
    type: str
    created_at: datetime.datetime
    edited_at: datetime.datetime | None


@dataclass(frozen=True, slots=True)
class FacultyFilterDTO(TimestampFilterDTOMixin):
    order_by: list[str] | None = None
    search: str | None = None
    principal_id: UUID | None = None
    principal_id__isnull: bool | None = None
    address_id: UUID | None = None
    address_id__isnull: bool | None = None
    university_id__isnull: bool | None = None
    university_id: UUID | None = None
