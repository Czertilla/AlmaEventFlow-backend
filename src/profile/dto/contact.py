from dataclasses import dataclass
from profile.enum.contact import ContactType
from uuid import UUID

from core.dto.base import FieldsSetDTOMixin


@dataclass(frozen=True, slots=True)
class ContactCreateDTO:
    person_id: UUID
    type: ContactType
    value: str
    is_main: bool = False


@dataclass(frozen=True, slots=True, kw_only=True)
class ContactPatchDTO(FieldsSetDTOMixin):
    id: UUID
    type: ContactType | None = None
    value: str | None = None
    is_main: bool | None = None


@dataclass(frozen=True, slots=True)
class ContactPutDTO:
    id: UUID
    person_id: UUID
    type: ContactType
    value: str
    is_main: bool = False


@dataclass(frozen=True, slots=True)
class ContactDTO:
    id: UUID
    person_id: UUID
    type: ContactType
    value: str
    is_main: bool


@dataclass(frozen=True, slots=True)
class ContactFilterDTO:
    order_by: list[str] | None = None
    search: str | None = None
    person_id: UUID | None = None
