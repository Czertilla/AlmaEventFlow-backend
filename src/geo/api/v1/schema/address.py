from pydantic import BaseModel, ConfigDict, computed_field, model_validator

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from core.schema.v1.mixin.model import PatchModelV1, UUIDMixinV1
from geo.api.v1.schema.city import CityCascadeCreate
from geo.api.v1.schema.point import Point
from geo.dto.address import (
    AddressCascadeCreateDTO,
    AddressCreateDTO,
    AddressFieldsDTO,
    AddressPatchDTO,
    AddressPutDTO,
)


class AddressFields(BaseModel, ToDTOMixinV1):
    __dto_cls__ = AddressFieldsDTO

    house: str | None = None
    district: str | None = None
    street: str | None = None
    building: str | None = None
    apartment: str | None = None

    def compose_name(self) -> str:
        parts = (self.street, self.house, self.building, self.apartment)
        return ", ".join(part.strip() for part in parts if part and part.strip())


class AddressBase(BaseModel):
    city_id: int
    name: str | None = None
    spot: Point | None = None
    parsed: AddressFields | None = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def _ensure_name(self) -> "AddressBase":
        if not (self.name and self.name.strip()) and self.parsed:
            self.name = self.parsed.compose_name()
        if not (self.name and self.name.strip()):
            raise ValueError("either name or parsed address fields are required")
        return self


class AddressCreate(AddressBase, ToDTOMixinV1):
    __dto_cls__ = AddressCreateDTO


class AddressRead(FromDTOMixinV1, AddressBase, UUIDMixinV1):
    name: str
    source: str | None = None

    @computed_field
    @property
    def map_uri(self) -> str | None:
        """RFC 5870 ``geo:`` URI -- the one scheme both Android and iOS
        resolve to whatever maps app the viewer actually has installed,
        without picking a specific provider (Google/Apple/Yandex/OsmAnd
        all register as handlers)."""
        if self.spot is None:
            return None
        return f"geo:{self.spot.lat},{self.spot.lon}"


class AddressPatchData(PatchModelV1):
    name: str | None = None
    city_id: int | None = None
    spot: Point | None = None
    parsed: AddressFields | None = None


class AddressPatch(AddressPatchData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = AddressPatchDTO


class AddressPutData(AddressBase): ...


class AddressPut(AddressPutData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = AddressPutDTO


class AddressCascadeCreate(AddressFields):
    __dto_cls__ = AddressCascadeCreateDTO

    city: CityCascadeCreate
    spot: Point | None = None

