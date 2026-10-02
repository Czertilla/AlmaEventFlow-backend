import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from core.schema.v1.mixin.model import PatchModelV1, TimestampMixinV1, UUIDMixinV1
from event.dto.event import EventCreateDTO, EventPatchDTO, EventPutDTO
from event.enum.format import EventFormatEnumV1
from event.enum.level import EventLevelEnumV1
from event.enum.status import EventStatusEnumV1
from event.enum.type import EventTypeEnumV1


class EventCreate(BaseModel, ToDTOMixinV1):
    __dto_cls__ = EventCreateDTO

    name: str = Field(max_length=128)
    date: datetime.date | None = None
    description: str | None = Field(max_length=1024, default=None)
    location_id: UUID | None = None
    organizer_id: UUID | None = None
    status: EventStatusEnumV1 = EventStatusEnumV1.draft
    level: EventLevelEnumV1 | None = None
    type: EventTypeEnumV1 | None = None
    format: EventFormatEnumV1 = EventFormatEnumV1.offline

    model_config = ConfigDict(from_attributes=True)


class EventRead(FromDTOMixinV1, EventCreate, UUIDMixinV1, TimestampMixinV1): ...


class EventPatchData(PatchModelV1):
    name: str | None = Field(max_length=128, default=None)
    date: datetime.date | None = None
    description: str | None = Field(max_length=1024, default=None)
    location_id: UUID | None = None
    organizer_id: UUID | None = None
    status: EventStatusEnumV1 = EventStatusEnumV1.draft
    level: EventLevelEnumV1 | None = None
    type: EventTypeEnumV1 | None = None
    format: EventFormatEnumV1 | None = None


class EventPatch(EventPatchData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = EventPatchDTO


class EventPutData(EventCreate): ...


class EventPut(EventPutData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = EventPutDTO
