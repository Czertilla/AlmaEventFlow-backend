import datetime
from dataclasses import dataclass
from uuid import UUID

from core.dto.base import FieldsSetDTOMixin, TimestampFilterDTOMixin
from geo.dto.city import CityCascadeCreateDTO
from geo.dto.point import PointDTO


@dataclass(frozen=True, slots=True)
class AddressFieldsDTO:
    house: str | None = None
    district: str | None = None
    street: str | None = None
    building: str | None = None
    apartment: str | None = None

    def compose_name(self) -> str:
        parts = (self.street, self.house, self.building, self.apartment)
        return ", ".join(part.strip() for part in parts if part and part.strip())


@dataclass(frozen=True, slots=True)
class AddressCreateDTO:
    city_id: int
    name: str | None = None
    spot: PointDTO | None = None
    parsed: AddressFieldsDTO | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class AddressPatchDTO(FieldsSetDTOMixin):
    id: UUID
    name: str | None = None
    city_id: int | None = None
    spot: PointDTO | None = None
    parsed: AddressFieldsDTO | None = None


@dataclass(frozen=True, slots=True)
class AddressPutDTO:
    id: UUID
    city_id: int
    name: str | None = None
    spot: PointDTO | None = None
    parsed: AddressFieldsDTO | None = None


@dataclass(frozen=True, slots=True)
class AddressCascadeCreateDTO:
    city: CityCascadeCreateDTO
    house: str | None = None
    district: str | None = None
    street: str | None = None
    building: str | None = None
    apartment: str | None = None
    spot: PointDTO | None = None


@dataclass(frozen=True, slots=True)
class AddressDTO:
    id: UUID
    city_id: int
    name: str
    spot: PointDTO | None
    parsed: AddressFieldsDTO | None
    source: str | None
    created_at: datetime.datetime
    edited_at: datetime.datetime | None


@dataclass(frozen=True, slots=True)
class AddressFilterDTO(TimestampFilterDTOMixin):
    order_by: list[str] | None = None
    search: str | None = None
    city_id: int | None = None
    city_id__in: list[int] | None = None
    source: str | None = None
    source__isnull: bool | None = None
    spot__isnull: bool | None = None
