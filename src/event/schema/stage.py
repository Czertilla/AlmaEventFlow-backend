from uuid import UUID
from pydantic import BaseModel, ConfigDict
from datetime import datetime

from core.utils.mixin.pydantic import PatchModel, UUIDMixin


class StageCreateData(BaseModel):
    name: str
    start_time: datetime
    end_time: datetime | None = None
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class StageCreate(StageCreateData):
    event_id: UUID


class StageRead(StageCreate, UUIDMixin): ...


class StagePatchData(PatchModel):
    name: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class StagePatch(StagePatchData, UUIDMixin): ...


class StagePutData(StageCreateData): ...


class StagePut(StagePutData, UUIDMixin): ...
