from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from core.dto.base import FieldsSetDTOMixin, TimestampFilterDTOMixin


@dataclass(frozen=True, slots=True)
class AttendanceCreateDTO:
    member_id: UUID
    participation_id: UUID
    is_attended: bool | None = False
    is_verified: bool | None = False
    comment: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class AttendanceMinePatchDTO(FieldsSetDTOMixin):
    is_attended: bool | None = None
    comment: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class AttendancePatchDTO(FieldsSetDTOMixin):
    id: UUID
    is_attended: bool | None = None
    is_verified: bool | None = None
    comment: str | None = None


@dataclass(frozen=True, slots=True)
class AttendancePutDTO:
    id: UUID
    member_id: UUID
    participation_id: UUID
    is_attended: bool | None = False
    is_verified: bool | None = False
    comment: str | None = None


@dataclass(frozen=True, slots=True)
class AttendanceDTO:
    id: UUID
    member_id: UUID
    participation_id: UUID
    is_attended: bool | None
    is_verified: bool | None
    comment: str | None
    created_at: datetime
    edited_at: datetime | None


@dataclass(frozen=True, slots=True)
class AttendanceFilterDTO(TimestampFilterDTOMixin):
    order_by: list[str] | None = None
    search: str | None = None
    participation_id: UUID | None = None
    participation_id__in: list[UUID] | None = None
    member_id: UUID | None = None
    member_id__in: list[UUID] | None = None
    is_attended: bool | None = None
    is_verified: bool | None = None
