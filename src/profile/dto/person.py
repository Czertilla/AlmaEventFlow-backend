import datetime
from dataclasses import dataclass
from uuid import UUID

from core.dto.base import FieldsSetDTOMixin, TimestampFilterDTOMixin


@dataclass(frozen=True, slots=True)
class PersonCreateDTO:
    surname: str
    name: str
    patronymic: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class PersonPatchDTO(FieldsSetDTOMixin):
    id: UUID
    surname: str | None = None
    name: str | None = None
    patronymic: str | None = None


@dataclass(frozen=True, slots=True)
class PersonPutDTO:
    id: UUID
    surname: str
    name: str
    patronymic: str | None = None


@dataclass(frozen=True, slots=True)
class PersonDTO:
    id: UUID
    surname: str
    name: str
    patronymic: str | None
    created_at: datetime.datetime
    edited_at: datetime.datetime | None


@dataclass(frozen=True, slots=True)
class PersonFilterDTO(TimestampFilterDTOMixin):
    order_by: list[str] | None = None
    search: str | None = None
