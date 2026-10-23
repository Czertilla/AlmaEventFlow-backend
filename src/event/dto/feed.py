import datetime
from dataclasses import dataclass, field
from enum import StrEnum, auto
from uuid import UUID

from event.dto.attendance import AttendanceViewDTO
from event.dto.member_profile import MemberPersonDTO
from event.dto.role import RolePreviewDTO
from event.enum.format import EventFormatEnumV1
from event.enum.level import EventLevelEnumV1
from event.enum.status import EventStatusEnumV1
from event.enum.type import EventTypeEnumV1


class FeedDirection(StrEnum):
    around = auto()
    past = auto()
    future = auto()


@dataclass(frozen=True, slots=True)
class EventKeyDTO:
    """Where an event stands in the date order: the date, then the id."""

    date: datetime.date
    id: UUID


@dataclass(frozen=True, slots=True)
class EventFilterViewDTO:
    statuses: list[EventStatusEnumV1] = field(default_factory=lambda: [])
    types: list[EventTypeEnumV1] = field(default_factory=lambda: [])
    levels: list[EventLevelEnumV1] = field(default_factory=lambda: [])
    formats: list[EventFormatEnumV1] = field(default_factory=lambda: [])
    collective_ids: list[UUID] = field(default_factory=lambda: [])
    date_from: datetime.date | None = None
    date_to: datetime.date | None = None


@dataclass(frozen=True, slots=True)
class FeedParamsDTO:
    direction: FeedDirection = FeedDirection.around
    anchor: datetime.date | None = None
    cursor: EventKeyDTO | None = None
    limit: int = 10
    filters: EventFilterViewDTO = field(default_factory=EventFilterViewDTO)


@dataclass(frozen=True, slots=True)
class PlaceDTO:
    id: UUID
    name: str | None
    lat: float | None
    lon: float | None


@dataclass(frozen=True, slots=True)
class CardParticipationDTO:
    id: UUID
    collective_id: UUID
    collective_name: str
    attended_count: int
    total_count: int
    my_attendance: AttendanceViewDTO | None


@dataclass(frozen=True, slots=True)
class EventCardDTO:
    id: UUID
    name: str
    date: datetime.date | None
    status: EventStatusEnumV1
    level: EventLevelEnumV1 | None
    type: EventTypeEnumV1 | None
    format: EventFormatEnumV1
    location: PlaceDTO | None
    starts_at: datetime.datetime | None
    ends_at: datetime.datetime | None
    participations: list[CardParticipationDTO]
    created_at: datetime.datetime
    edited_at: datetime.datetime | None
    updated_at: datetime.datetime


@dataclass(frozen=True, slots=True)
class FeedDTO:
    items: list[EventCardDTO]
    has_more_past: bool
    has_more_future: bool
    past_cursor: EventKeyDTO | None
    future_cursor: EventKeyDTO | None


@dataclass(frozen=True, slots=True)
class ViewerCollectiveDTO:
    id: UUID
    name: str
    is_verified: bool
    is_principal: bool
    member_id: UUID | None
    member_is_active: bool | None
    roles: list[RolePreviewDTO]


@dataclass(frozen=True, slots=True)
class ViewerContextDTO:
    person_id: UUID | None
    is_superuser: bool
    collectives: list[ViewerCollectiveDTO]


@dataclass(frozen=True, slots=True)
class RosterMemberDTO:
    id: UUID
    person: MemberPersonDTO
    is_active: bool
    roles: list[RolePreviewDTO]
