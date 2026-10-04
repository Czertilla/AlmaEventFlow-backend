import datetime
from dataclasses import dataclass, field
from uuid import UUID

from core.dto.base import FieldsSetDTOMixin, TimestampFilterDTOMixin
from event.dto.role import RolePreviewDTO


@dataclass(frozen=True, slots=True)
class MemberCreateDataDTO:
    person_id: UUID
    roles: list[UUID] = field(default_factory=list)
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class MemberCreateDTO:
    collective_id: UUID
    person_id: UUID
    roles: list[UUID] = field(default_factory=list)
    is_active: bool = True


@dataclass(frozen=True, slots=True, kw_only=True)
class MemberPatchRolesDTO(FieldsSetDTOMixin):
    roles: list[UUID] | None = None
    is_active: bool | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class MemberPatchDTO(FieldsSetDTOMixin):
    id: UUID
    roles: list[UUID] | None = None
    is_active: bool | None = None


@dataclass(frozen=True, slots=True)
class MemberPutDTO:
    id: UUID
    roles: list[UUID] = field(default_factory=list)
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class MemberDTO:
    id: UUID
    collective_id: UUID
    person_id: UUID
    is_active: bool
    roles: list[RolePreviewDTO]
    created_at: datetime.datetime
    edited_at: datetime.datetime | None


@dataclass(frozen=True, slots=True)
class MemberFilterDTO(TimestampFilterDTOMixin):
    order_by: list[str] | None = None
    search: str | None = None
    is_active: bool = True
    collective_id: UUID | None = None
    collective_id__in: list[UUID] | None = None
    person_id: UUID | None = None
    person_id__in: list[UUID] | None = None
