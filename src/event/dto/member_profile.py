import datetime
from dataclasses import dataclass
from uuid import UUID

from event.dto.member import MemberDTO
from event.enum.attendance import AttendanceOutcomeEnumV1
from event.enum.status import EventStatusEnumV1
from event.enum.type import EventTypeEnumV1


@dataclass(frozen=True, slots=True)
class MemberProfilePeriodDTO:
    date_from: datetime.date | None = None
    date_to: datetime.date | None = None


@dataclass(frozen=True, slots=True)
class ProfileViewerDTO:
    person_id: UUID | None
    is_superuser: bool = False


@dataclass(frozen=True, slots=True)
class MemberPersonDTO:
    id: UUID
    surname: str
    name: str
    patronymic: str | None


@dataclass(frozen=True, slots=True)
class MemberAttendanceItemDTO:
    attendance_id: UUID
    event_id: UUID
    event_name: str
    date: datetime.date
    status: EventStatusEnumV1
    type: EventTypeEnumV1 | None
    outcome: AttendanceOutcomeEnumV1
    is_attended: bool | None
    is_verified: bool
    comment: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class AttendanceCountsDTO:
    attended: int
    absent: int
    unmarked: int
    upcoming: int


@dataclass(frozen=True, slots=True, kw_only=True)
class AttendanceByTypeDTO(AttendanceCountsDTO):
    type: EventTypeEnumV1 | None


@dataclass(frozen=True, slots=True, kw_only=True)
class AttendanceByMonthDTO(AttendanceCountsDTO):
    month: datetime.date


@dataclass(frozen=True, slots=True, kw_only=True)
class MemberAttendanceSummaryDTO(AttendanceCountsDTO):
    past: int
    verified: int
    rate: float | None
    current_streak: int
    longest_streak: int
    last_attended: datetime.date | None


@dataclass(frozen=True, slots=True)
class MemberProfileDTO:
    member: MemberDTO
    person: MemberPersonDTO
    can_manage: bool
    date_from: datetime.date
    date_to: datetime.date
    years: list[int]
    summary: MemberAttendanceSummaryDTO
    by_type: list[AttendanceByTypeDTO]
    by_month: list[AttendanceByMonthDTO]
    items: list[MemberAttendanceItemDTO]
