import datetime
from dataclasses import dataclass
from uuid import UUID

from core.dto.base import FieldsSetDTOMixin
from event.enum.format import EventFormatEnumV1
from event.enum.level import EventLevelEnumV1
from event.enum.status import EventStatusEnumV1
from event.enum.type import EventTypeEnumV1


@dataclass(frozen=True, slots=True)
class EventDTO:
    id: UUID
    name: str
    date: datetime.date | None
    description: str | None
    location_id: UUID | None
    organizer_id: UUID | None
    status: EventStatusEnumV1
    level: EventLevelEnumV1 | None
    type: EventTypeEnumV1 | None
    format: EventFormatEnumV1
    created_at: datetime.datetime
    edited_at: datetime.datetime | None


@dataclass(frozen=True, slots=True)
class EventCreateDTO:
    name: str
    date: datetime.date | None = None
    description: str | None = None
    location_id: UUID | None = None
    organizer_id: UUID | None = None
    status: EventStatusEnumV1 = EventStatusEnumV1.draft
    level: EventLevelEnumV1 | None = None
    type: EventTypeEnumV1 | None = None
    format: EventFormatEnumV1 = EventFormatEnumV1.offline


@dataclass(frozen=True, slots=True, kw_only=True)
class EventPatchDTO(FieldsSetDTOMixin):
    id: UUID
    name: str | None = None
    date: datetime.date | None = None
    description: str | None = None
    location_id: UUID | None = None
    organizer_id: UUID | None = None
    status: EventStatusEnumV1 = EventStatusEnumV1.draft
    level: EventLevelEnumV1 | None = None
    type: EventTypeEnumV1 | None = None
    format: EventFormatEnumV1 | None = None


@dataclass(frozen=True, slots=True)
class EventPutDTO:
    id: UUID
    name: str
    date: datetime.date | None = None
    description: str | None = None
    location_id: UUID | None = None
    organizer_id: UUID | None = None
    status: EventStatusEnumV1 = EventStatusEnumV1.draft
    level: EventLevelEnumV1 | None = None
    type: EventTypeEnumV1 | None = None
    format: EventFormatEnumV1 = EventFormatEnumV1.offline


@dataclass(frozen=True, slots=True)
class EventFilterDTO:
    order_by: list[str] | None = None
    search: str | None = None
    status: EventStatusEnumV1 | None = None
    level: EventLevelEnumV1 | None = None
    type: EventTypeEnumV1 | None = None
    format: EventFormatEnumV1 | None = None
    date__gte: datetime.date | None = None
    date__lte: datetime.date | None = None
    level__in: list[EventLevelEnumV1] | None = None
    type__in: list[EventTypeEnumV1] | None = None
    format__in: list[EventFormatEnumV1] | None = None
    participant_id: UUID | None = None
    participant_id__in: list[UUID] | None = None
