from dataclasses import dataclass
from uuid import UUID

from fastapi import UploadFile

from core.dto.base import FieldsSetDTOMixin


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
    participation_id: UUID
    name: str
    degree: int | None
    file_link: str | None = None


@dataclass(frozen=True, slots=True)
class RewardFilterDTO:
    order_by: list[str] | None = None
    search: str | None = None
