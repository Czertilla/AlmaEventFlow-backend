import datetime
from dataclasses import dataclass
from uuid import UUID

from core.dto.base import FieldsSetDTOMixin


@dataclass(frozen=True, slots=True)
class NameVariantCreateDTO:
    surname: str
    name: str
    patronymic: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class NameVariantPatchDataDTO(FieldsSetDTOMixin):
    surname: str | None = None
    name: str | None = None
    patronymic: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class NameVariantPatchDTO(FieldsSetDTOMixin):
    id: UUID
    surname: str | None = None
    name: str | None = None
    patronymic: str | None = None


@dataclass(frozen=True, slots=True)
class NameVariantPutDTO:
    id: UUID
    surname: str
    name: str
    patronymic: str | None = None


@dataclass(frozen=True, slots=True)
class NameVariantDTO:
    id: UUID
    surname: str
    name: str
    patronymic: str | None


@dataclass(frozen=True, slots=True)
class PassportCreateDTO:
    profile_id: UUID
    number: str
    expire_date: datetime.date
    is_foreign: bool
    issued_date: datetime.date | None = None
    issued_authority: str | None = None
    name_variant: NameVariantCreateDTO | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class PassportPatchDTO(FieldsSetDTOMixin):
    id: UUID
    number: str | None = None
    name_variant: NameVariantPatchDataDTO | None = None
    expire_date: datetime.date | None = None
    is_foreign: bool | None = None
    issued_date: datetime.date | None = None
    issued_authority: str | None = None


@dataclass(frozen=True, slots=True)
class PassportPutDTO:
    id: UUID
    profile_id: UUID
    number: str
    expire_date: datetime.date
    is_foreign: bool
    issued_date: datetime.date | None = None
    issued_authority: str | None = None
    name_variant: NameVariantCreateDTO | None = None


@dataclass(frozen=True, slots=True)
class PassportDTO:
    id: UUID
    profile_id: UUID
    number: str
    expire_date: datetime.date
    is_foreign: bool
    issued_date: datetime.date | None
    issued_authority: str | None
    name_variant: NameVariantCreateDTO | None


@dataclass(frozen=True, slots=True)
class PassportFilterDTO:
    order_by: list[str] | None = None
    search: str | None = None
    profile_id: UUID | None = None
