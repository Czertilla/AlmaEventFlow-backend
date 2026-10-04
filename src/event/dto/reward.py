import datetime
from dataclasses import dataclass
from uuid import UUID

from fastapi import UploadFile

from core.dto.base import FieldsSetDTOMixin, TimestampFilterDTOMixin


@dataclass(frozen=True, slots=True)
class RewardCreateDTO:
    participation_id: UUID
    name: str
    degree: int | None = None
    file: UploadFile | None = None  # live upload stream, passed through unread


@dataclass(frozen=True, slots=True, kw_only=True)
class RewardPatchDTO(FieldsSetDTOMixin):
    id: UUID
    name: str | None = None
    degree: int | None = None
    file: UploadFile | None = None


@dataclass(frozen=True, slots=True)
class RewardPutDTO:
    id: UUID
    name: str
    degree: int | None = None


@dataclass(frozen=True, slots=True)
class RewardDTO:
    id: UUID
    participation_id: UUID | None
    name: str
    degree: int | None
    created_at: datetime.datetime
    edited_at: datetime.datetime | None
    file_link: str | None = None


@dataclass(frozen=True, slots=True)
class RewardFilterDTO(TimestampFilterDTOMixin):
    order_by: list[str] | None = None
    search: str | None = None
    participation_id: UUID | None = None
    participation_id__in: list[UUID] | None = None
    degree: int | None = None
    degree__in: list[int] | None = None
    degree__isnull: bool | None = None
