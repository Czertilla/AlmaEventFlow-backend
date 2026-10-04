import datetime
from dataclasses import dataclass
from profile.dto.diet import DietDTO
from profile.dto.organization import OrganizationDTO
from profile.dto.person import PersonDTO
from uuid import UUID

from core.dto.base import FieldsSetDTOMixin, TimestampFilterDTOMixin


@dataclass(frozen=True, slots=True)
class ProfileCreateDTO:
    id: UUID
    birthdate: datetime.date | None = None
    workplace_id: UUID | None = None
    diet_id: int | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class ProfilePatchDTO(FieldsSetDTOMixin):
    id: UUID
    birthdate: datetime.date | None = None
    workplace_id: UUID | None = None
    diet_id: int | None = None


@dataclass(frozen=True, slots=True)
class ProfilePutDTO:
    id: UUID
    birthdate: datetime.date | None = None
    workplace_id: UUID | None = None
    diet_id: int | None = None


@dataclass(frozen=True, slots=True)
class ProfileDTO:
    id: UUID
    birthdate: datetime.date | None
    workplace_id: UUID | None
    diet_id: int | None
    created_at: datetime.datetime
    edited_at: datetime.datetime | None
    person: PersonDTO | None
    diet: DietDTO | None
    workplace: OrganizationDTO | None


@dataclass(frozen=True, slots=True)
class ProfileFilterDTO(TimestampFilterDTOMixin):
    order_by: list[str] | None = None
    search: str | None = None
    birthdate__gte: datetime.date | None = None
    birthdate__lte: datetime.date | None = None
    birthdate__isnull: bool | None = None
    workplace_id: UUID | None = None
    workplace_id__isnull: bool | None = None
    diet_id: int | None = None
    diet_id__in: list[int] | None = None
    diet_id__isnull: bool | None = None
