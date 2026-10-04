import datetime
from dataclasses import dataclass
from uuid import UUID

from core.dto.base import FieldsSetDTOMixin, TimestampFilterDTOMixin
from geo.dto.address import AddressDTO
from geo.dto.point import PointDTO


@dataclass(frozen=True, slots=True)
class LocationCreateDTO:
    name: str | None = None
    address_id: UUID | None = None
    spot: PointDTO | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class LocationPatchDTO(FieldsSetDTOMixin):
    id: UUID
    name: str | None = None
    address_id: UUID | None = None
    spot: PointDTO | None = None


@dataclass(frozen=True, slots=True)
class LocationPutDTO:
    id: UUID
    name: str | None = None
    address_id: UUID | None = None
    spot: PointDTO | None = None


@dataclass(frozen=True, slots=True)
class LocationDTO:
    id: UUID
    name: str | None
    address_id: UUID | None
    spot: PointDTO | None
    address: AddressDTO | None
    created_at: datetime.datetime
    edited_at: datetime.datetime | None


@dataclass(frozen=True, slots=True)
class LocationFilterDTO(TimestampFilterDTOMixin):
    order_by: list[str] | None = None
    search: str | None = None
    address_id: UUID | None = None
    address_id__in: list[UUID] | None = None
    name__isnull: bool | None = None
    spot__isnull: bool | None = None
