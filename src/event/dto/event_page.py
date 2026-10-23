import datetime
from dataclasses import dataclass
from uuid import UUID

from event.dto.feed import PlaceDTO, RosterMemberDTO
from event.dto.stage import StageDTO
from event.enum.format import EventFormatEnumV1
from event.enum.level import EventLevelEnumV1
from event.enum.priority import EventPriorityEnumV1
from event.enum.status import EventStatusEnumV1
from event.enum.type import EventTypeEnumV1


@dataclass(frozen=True, slots=True)
class PageEventDTO:
    id: UUID
    name: str
    date: datetime.date | None
    description: str | None
    status: EventStatusEnumV1
    level: EventLevelEnumV1 | None
    type: EventTypeEnumV1 | None
    format: EventFormatEnumV1
    organizer_id: UUID | None
    location_id: UUID | None
    location: PlaceDTO | None
    created_at: datetime.datetime
    edited_at: datetime.datetime | None


@dataclass(frozen=True, slots=True)
class PageAttendanceDTO:
    id: UUID
    member_id: UUID
    participation_id: UUID
    is_attended: bool | None
    is_verified: bool
    comment: str | None
    created_at: datetime.datetime
    edited_at: datetime.datetime | None
    member: RosterMemberDTO


@dataclass(frozen=True, slots=True)
class PageParticipationDTO:
    id: UUID
    collective_id: UUID
    collective_name: str
    priority_degree: EventPriorityEnumV1 | None
    is_principal: bool
    is_member: bool
    can_view_attendances: bool
    attended_count: int | None
    total_count: int | None
    my_attendance_id: UUID | None
    attendances: list[PageAttendanceDTO]
    addable_members: list[RosterMemberDTO]


@dataclass(frozen=True, slots=True)
class EventPageDTO:
    event: PageEventDTO
    stages: list[StageDTO]
    participations: list[PageParticipationDTO]
    editable_collective_id: UUID | None
