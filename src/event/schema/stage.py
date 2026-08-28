from datetime import datetime
from uuid import UUID
from zoneinfo import available_timezones

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.utils.mixin.pydantic import PatchModel, UUIDMixin

_VALID_TIMEZONES = available_timezones()


def _validate_timezone(value: str | None) -> str | None:
    if value is not None and value not in _VALID_TIMEZONES:
        raise ValueError(f"unknown IANA timezone: {value!r}")
    return value


class StageCreateData(BaseModel):
    name: str = Field(max_length=32)
    start_at: datetime
    end_at: datetime | None = None
    description: str | None = Field(max_length=1024, default=None)
    timezone: str | None = None
    """IANA zone name of the client creating this stage (e.g.
    ``Europe/Moscow``), so displays that can't pick a per-viewer zone (the
    Telegram bot) can still show the time the creator meant."""

    model_config = ConfigDict(from_attributes=True)

    _validate_timezone = field_validator("timezone")(_validate_timezone)


class StageCreate(StageCreateData):
    event_id: UUID


class StageRead(StageCreate, UUIDMixin): ...


class StagePatchData(PatchModel):
    name: str | None = Field(max_length=32, default=None)
    start_at: datetime | None = None
    end_at: datetime | None = None
    description: str | None = Field(max_length=1024, default=None)
    timezone: str | None = None

    model_config = ConfigDict(from_attributes=True)

    _validate_timezone = field_validator("timezone")(_validate_timezone)


class StagePatch(StagePatchData, UUIDMixin): ...


class StagePutData(StageCreateData): ...


class StagePut(StagePutData, UUIDMixin): ...
