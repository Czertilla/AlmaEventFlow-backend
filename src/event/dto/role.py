import datetime
from dataclasses import dataclass
from uuid import UUID

from core.dto.base import FieldsSetDTOMixin, TimestampFilterDTOMixin


@dataclass(frozen=True, slots=True)
class RolePreviewDTO:
    id: UUID
    name: str


@dataclass(frozen=True, slots=True)
class RoleCreateDTO:
    collective_id: UUID
    name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class RolePatchDTO(FieldsSetDTOMixin):
    id: UUID
    name: str | None = None


@dataclass(frozen=True, slots=True)
class RolePutDTO:
    id: UUID
    name: str


@dataclass(frozen=True, slots=True)
class RoleDTO:
    id: UUID
    collective_id: UUID
    name: str
    created_at: datetime.datetime
    edited_at: datetime.datetime | None


@dataclass(frozen=True, slots=True)
class RoleFilterDTO(TimestampFilterDTOMixin):
    order_by: list[str] | None = None
    search: str | None = None
    collective_id: UUID | None = None
    collective_id__in: list[UUID] | None = None
