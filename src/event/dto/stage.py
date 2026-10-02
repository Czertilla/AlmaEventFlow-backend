from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from core.dto.base import FieldsSetDTOMixin


@dataclass(frozen=True, slots=True)
class StageCreateDataDTO:
    name: str
    start_at: datetime
    end_at: datetime | None = None
    description: str | None = None
    timezone: str | None = None


@dataclass(frozen=True, slots=True)
class StageCreateDTO:
    event_id: UUID
    name: str
    start_at: datetime
    end_at: datetime | None = None
    description: str | None = None
    timezone: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class StagePatchDTO(FieldsSetDTOMixin):
    id: UUID
    name: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    description: str | None = None
    timezone: str | None = None


@dataclass(frozen=True, slots=True)
class StagePutDTO:
    id: UUID
    name: str
    start_at: datetime
    end_at: datetime | None = None
    description: str | None = None
    timezone: str | None = None


@dataclass(frozen=True, slots=True)
class StageDTO:
    id: UUID
    event_id: UUID
    name: str
    start_at: datetime
    end_at: datetime | None
    description: str | None
    timezone: str | None


@dataclass(frozen=True, slots=True)
class StageFilterDTO:
    order_by: list[str] | None = None
    search: str | None = None
    event_id: UUID | None = None
    event_id__in: list[UUID] | None = None
