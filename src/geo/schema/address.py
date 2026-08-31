from pydantic import BaseModel, ConfigDict, computed_field

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


class AddressPatchData(PatchModel):
    parsed: AddressFieldsPatchData | None = None


class AddressPatch(AddressPatchData, UUIDMixin): ...


class AddressPutData(AddressCreate): ...


class AddressPut(AddressPutData, UUIDMixin): ...


class AddressCascadeCreate(AddressFields):
    city: CityCascadeCreate
    spot: Point | None = None

