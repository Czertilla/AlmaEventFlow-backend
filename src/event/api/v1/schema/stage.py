from datetime import datetime
from uuid import UUID
from zoneinfo import available_timezones

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from core.schema.v1.mixin.model import PatchModelV1, TimestampMixinV1, UUIDMixinV1
from event.dto.stage import (
    StageCreateDataDTO,
    StageCreateDTO,
    StagePatchDTO,
    StagePutDTO,
)

_VALID_TIMEZONES = available_timezones()


def _validate_timezone(value: str | None) -> str | None:
    if value is not None and value not in _VALID_TIMEZONES:
        raise ValueError(f"unknown IANA timezone: {value!r}")
    return value


def _check_span(start: datetime | None, end: datetime | None) -> None:
    if start is not None and end is not None and end < start:
        raise ValueError("end_at must not be earlier than start_at")


class StageFields(BaseModel):
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


class StageCreateData(StageFields, ToDTOMixinV1):
    __dto_cls__ = StageCreateDataDTO

    @model_validator(mode="after")
    def _validate_span(self) -> "StageCreateData":
        _check_span(self.start_at, self.end_at)
        return self


class StageCreate(StageCreateData, ToDTOMixinV1):
    __dto_cls__ = StageCreateDTO

    event_id: UUID


class StageRead(FromDTOMixinV1, StageFields, UUIDMixinV1, TimestampMixinV1):
    event_id: UUID


class StagePatchData(PatchModelV1):
    name: str | None = Field(max_length=32, default=None)
    start_at: datetime | None = None
    end_at: datetime | None = None
    description: str | None = Field(max_length=1024, default=None)
    timezone: str | None = None

    model_config = ConfigDict(from_attributes=True)

    _validate_timezone = field_validator("timezone")(_validate_timezone)

    @model_validator(mode="after")
    def _validate_span(self) -> "StagePatchData":
        _check_span(self.start_at, self.end_at)
        return self


class StagePatch(StagePatchData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = StagePatchDTO


class StagePutData(StageCreateData): ...


class StagePut(StagePutData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = StagePutDTO
