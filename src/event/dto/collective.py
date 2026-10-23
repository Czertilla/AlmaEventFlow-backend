from dataclasses import dataclass
from uuid import UUID

from core.dto.base import FieldsSetDTOMixin


@dataclass(frozen=True, slots=True)
class CollectiveSummaryDTO:
    id: UUID
    name: str
    principal_id: UUID
    is_verified: bool


@dataclass(frozen=True, slots=True)
class CollectiveDTO:
    id: UUID
    name: str
    principal_id: UUID | None
    is_verified: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class CollectivePatchDTO(FieldsSetDTOMixin):
    id: UUID
    is_verified: bool | None = None


@dataclass(frozen=True, slots=True)
class CollectiveFilterDTO:
    id: UUID | None = None
    id__in: list[UUID] | None = None
    order_by: list[str] | None = None
    search: str | None = None
    principal_id: UUID | None = None
    principal_id__in: list[UUID] | None = None
    is_verified: bool | None = None
