import datetime
from dataclasses import dataclass
from uuid import UUID

from event.dto.member_profile import (
    AttendanceByMonthDTO,
    AttendanceByTypeDTO,
    AttendanceCountsDTO,
    MemberPersonDTO,
)
from event.enum.status import EventStatusEnumV1
from event.enum.type import EventTypeEnumV1


@dataclass(frozen=True, slots=True)
class CollectiveInfoDTO:
    id: UUID
    name: str
    is_verified: bool
    principal: MemberPersonDTO | None
    active_members: int


@dataclass(frozen=True, slots=True, kw_only=True)
class CollectiveAttendanceSummaryDTO(AttendanceCountsDTO):
    past: int
    verified: int
    rate: float | None
    events: int


@dataclass(frozen=True, slots=True, kw_only=True)
class CollectiveDayDTO(AttendanceCountsDTO):
    date: datetime.date


@dataclass(frozen=True, slots=True, kw_only=True)
class CollectiveEventItemDTO(AttendanceCountsDTO):
    event_id: UUID
    event_name: str
    date: datetime.date
    status: EventStatusEnumV1
    type: EventTypeEnumV1 | None


@dataclass(frozen=True, slots=True, kw_only=True)
class CollectiveMemberItemDTO(AttendanceCountsDTO):
    member_id: UUID
    person: MemberPersonDTO
    is_active: bool
    past: int
    rate: float | None


@dataclass(frozen=True, slots=True)
class CollectiveProfileDTO:
    collective: CollectiveInfoDTO
    can_manage: bool
    date_from: datetime.date
    date_to: datetime.date
    years: list[int]
    summary: CollectiveAttendanceSummaryDTO
    by_type: list[AttendanceByTypeDTO]
    by_month: list[AttendanceByMonthDTO]
    days: list[CollectiveDayDTO]
    events: list[CollectiveEventItemDTO]
    members: list[CollectiveMemberItemDTO]
