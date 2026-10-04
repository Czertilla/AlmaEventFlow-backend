import datetime
from dataclasses import dataclass
from uuid import UUID

from core.dto.base import FieldsSetDTOMixin, TimestampFilterDTOMixin
from event.enum.priority import EventPriorityEnumV1


@dataclass(frozen=True, slots=True)
class ParticipationCreateDataDTO:
    event_id: UUID
    priority_degree: EventPriorityEnumV1 | None = None


@dataclass(frozen=True, slots=True)
class ParticipationCreateDTO:
    event_id: UUID
    collective_id: UUID
    priority_degree: EventPriorityEnumV1 | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class ParticipationPatchDTO(FieldsSetDTOMixin):
    id: UUID
    event_id: UUID | None = None
    priority_degree: EventPriorityEnumV1 | None = None


@dataclass(frozen=True, slots=True)
class ParticipationPutDTO:
    id: UUID
    event_id: UUID
    priority_degree: EventPriorityEnumV1 | None = None


@dataclass(frozen=True, slots=True)
class ParticipationDTO:
    id: UUID
    event_id: UUID
    collective_id: UUID
    priority_degree: EventPriorityEnumV1 | None
    created_at: datetime.datetime
    edited_at: datetime.datetime | None
    collective_name: str | None = None


@dataclass(frozen=True, slots=True)
class ParticipationFilterDTO(TimestampFilterDTOMixin):
    order_by: list[str] | None = None
    collective_id: UUID | None = None
    collective_id__in: list[UUID] | None = None
    event_id: UUID | None = None
    event_id__in: list[UUID] | None = None
    priority_degree: EventPriorityEnumV1 | None = None
    priority_degree__in: list[EventPriorityEnumV1] | None = None
    priority_degree__isnull: bool | None = None
