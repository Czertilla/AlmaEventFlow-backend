import datetime
from dataclasses import dataclass
from uuid import UUID

from core.dto.base import FieldsSetDTOMixin
from event.dto.stage import StageCreateDataDTO
from event.enum.format import EventFormatEnumV1
from event.enum.level import EventLevelEnumV1
from event.enum.priority import EventPriorityEnumV1
from event.enum.status import EventStatusEnumV1
from event.enum.type import EventTypeEnumV1


@dataclass(frozen=True, slots=True)
class MeParticipationCreateDTO:
    event_id: UUID
    priority_degree: EventPriorityEnumV1 | None = None
    member_ids: list[UUID] | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class MeEventCreateDTO(FieldsSetDTOMixin):
    collective_id: UUID
    name: str
    date: datetime.date | None = None
    description: str | None = None
    location_id: UUID | None = None
    organizer_id: UUID | None = None
    status: EventStatusEnumV1 = EventStatusEnumV1.draft
    level: EventLevelEnumV1 | None = None
    type: EventTypeEnumV1 | None = None
    format: EventFormatEnumV1 = EventFormatEnumV1.offline
    member_ids: list[UUID] | None = None
    stages: list[StageCreateDataDTO] | None = None
    template_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class MeEventDTO:
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
    participation_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class MeAttendanceCreateDataDTO:
    member_id: UUID
    is_attended: bool | None = True
    is_verified: bool | None = False
    comment: str | None = None
