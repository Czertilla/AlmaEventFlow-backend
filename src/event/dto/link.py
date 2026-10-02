from dataclasses import dataclass
from uuid import UUID

from core.dto.base import FieldsSetDTOMixin
from event.enum.link import EventLinkTypeEnumV1


@dataclass(frozen=True, slots=True)
class LinkCreateDataDTO:
    url: str
    type: EventLinkTypeEnumV1
    description: str | None = None


@dataclass(frozen=True, slots=True)
class LinkCreateDTO:
    event_id: UUID
    url: str
    type: EventLinkTypeEnumV1
    description: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class LinkPatchDTO(FieldsSetDTOMixin):
    id: UUID
    url: str | None = None
    type: str | None = None
    description: str | None = None


@dataclass(frozen=True, slots=True)
class LinkPutDTO:
    id: UUID
    url: str
    type: EventLinkTypeEnumV1
    description: str | None = None


@dataclass(frozen=True, slots=True)
class LinkDTO:
    id: UUID
    event_id: UUID
    url: str
    type: EventLinkTypeEnumV1
    description: str | None


@dataclass(frozen=True, slots=True)
class LinkFilterDTO:
    order_by: list[str] | None = None
    search: str | None = None
