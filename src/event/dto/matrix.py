import datetime
from dataclasses import dataclass
from uuid import UUID

from event.dto.attendance import AttendanceViewDTO
from event.dto.feed import EventKeyDTO, FeedDirection, PlaceDTO, RosterMemberDTO
from event.dto.role import RoleDTO
from event.enum.format import EventFormatEnumV1
from event.enum.level import EventLevelEnumV1
from event.enum.status import EventStatusEnumV1
from event.enum.type import EventTypeEnumV1


@dataclass(frozen=True, slots=True)
class CollectiveEventDTO:
    id: UUID
    name: str
    date: datetime.date | None
    status: EventStatusEnumV1
    level: EventLevelEnumV1 | None
    type: EventTypeEnumV1 | None
    format: EventFormatEnumV1
    location: PlaceDTO | None
    participation_id: UUID
    created_at: datetime.datetime
    edited_at: datetime.datetime | None


@dataclass(frozen=True, slots=True)
class RosterDTO:
    members: list[RosterMemberDTO]
    roles: list[RoleDTO]


@dataclass(frozen=True, slots=True)
class CollectiveEventsDTO:
    items: list[CollectiveEventDTO]
    truncated: bool


@dataclass(frozen=True, slots=True)
class MatrixParamsDTO:
    direction: FeedDirection = FeedDirection.around
    anchor: datetime.date | None = None
    cursor: EventKeyDTO | None = None
    limit: int = 20
    date_from: datetime.date | None = None
    date_to: datetime.date | None = None


@dataclass(frozen=True, slots=True)
class MatrixDTO:
    members: list[RosterMemberDTO]
    roles: list[RoleDTO]
    events: list[CollectiveEventDTO]
    attendances: list[AttendanceViewDTO]
    has_more_past: bool
    has_more_future: bool
    past_cursor: EventKeyDTO | None
    future_cursor: EventKeyDTO | None
