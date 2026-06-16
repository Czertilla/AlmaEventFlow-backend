from pydantic import BaseModel, ConfigDict
from core.utils.mixin.pydantic import PatchModel, UUIDMixin
from geo.schema.city import CityCascadeCreate
from geo.schema.point import Point


class AddressFields(BaseModel):
    house: str
    district: str | None = None
    street: str | None = None
    building: str | None = None
    apartment: str | None = None

class AddressFieldsPatchData(AddressFields):
    house: str | None = None
    city_id: int | None = None
    spot: Point | None = None


class AddressCreate(BaseModel):
    city_id: int
    name: str | None = None
    spot: Point | None = None
    parsed: AddressFields | None = None

    model_config = ConfigDict(from_attributes=True)


class AddressRead(AddressCreate, UUIDMixin):
    name: str


class AddressPatchData(PatchModel):
    parsed: AddressFieldsPatchData | None = None


class AddressPatch(AddressPatchData, UUIDMixin): ...


class AddressPutData(AddressCreate): ...


class AddressPut(AddressPutData, UUIDMixin): ...


class AddressCascadeCreate(AddressFields):
    city: CityCascadeCreate
    spot: Point | None = None

