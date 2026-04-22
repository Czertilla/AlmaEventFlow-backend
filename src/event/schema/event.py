from uuid import UUID
from pydantic import BaseModel, ConfigDict
import datetime

from core.utils.mixin.pydantic import PatchModel, TimestampMixin, UUIDMixin


class EventCreate(BaseModel):
    name: str
    date: datetime.date | None = None
    description: str | None = None
    location_id: UUID | None = None
    organizer_id: UUID | None = None
    status_id: int = 0

    model_config = ConfigDict(from_attributes=True)


class EventRead(EventCreate, UUIDMixin, TimestampMixin): ...


class EventPatchData(PatchModel):
    name: str | None = None
    date: datetime.date | None = None
    description: str | None = None
    location_id: UUID | None = None
    organizer_id: UUID | None = None
    status_id: int = 0


class EventPatch(EventPatchData, UUIDMixin): ...


class EventPutData(EventCreate): ...


class EventPut(EventPutData, UUIDMixin): ...
