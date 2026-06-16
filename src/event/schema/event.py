from uuid import UUID
from pydantic import BaseModel, ConfigDict
import datetime

from core.utils.mixin.pydantic import PatchModel, TimestampMixin, UUIDMixin
from event.enum.format import EventFormatEnumV1
from event.enum.level import EventLevelEnumV1
from event.enum.status import EventStatusEnumV1
from event.enum.type import EventTypeEnumV1


class EventCreate(BaseModel):
    name: str
    date: datetime.date | None = None
    description: str | None = None
    location_id: UUID | None = None
    organizer_id: UUID | None = None
    status: EventStatusEnumV1 = EventStatusEnumV1.draft
    level: EventLevelEnumV1 | None = None
    type: EventTypeEnumV1 | None = None
    format: EventFormatEnumV1 = EventFormatEnumV1.offline

    model_config = ConfigDict(from_attributes=True)


class EventRead(EventCreate, UUIDMixin, TimestampMixin): ...


class EventPatchData(PatchModel):
    name: str | None = None
    date: datetime.date | None = None
    description: str | None = None
    location_id: UUID | None = None
    organizer_id: UUID | None = None
    status: EventStatusEnumV1 = EventStatusEnumV1.draft
    level: EventLevelEnumV1 | None = None
    type: EventTypeEnumV1 | None = None
    format: EventFormatEnumV1 | None = None


class EventPatch(EventPatchData, UUIDMixin): ...


class EventPutData(EventCreate): ...


class EventPut(EventPutData, UUIDMixin): ...
