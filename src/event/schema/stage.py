from uuid import UUID
from pydantic import BaseModel, ConfigDict
from datetime import datetime

from core.utils.mixin.pydantic import PatchModel, UUIDMixin


class StageCreateData(BaseModel):
    name: str
    start_at: datetime
    end_at: datetime | None = None
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class StageCreate(StageCreateData):
    event_id: UUID


class StageRead(StageCreate, UUIDMixin): ...


class StagePatchData(PatchModel):
    name: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class StagePatch(StagePatchData, UUIDMixin): ...


class StagePutData(StageCreateData): ...


class StagePut(StagePutData, UUIDMixin): ...
