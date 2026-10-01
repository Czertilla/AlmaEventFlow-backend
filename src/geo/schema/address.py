from pydantic import BaseModel, ConfigDict, computed_field, model_validator

from core.utils.mixin.pydantic import PatchModel, UUIDMixin
from geo.schema.city import CityCascadeCreate
from geo.schema.point import Point


class AddressFields(BaseModel):
    house: str | None = None
    district: str | None = None
    street: str | None = None
    building: str | None = None
    apartment: str | None = None

    def compose_name(self) -> str:
        parts = (self.street, self.house, self.building, self.apartment)
        return ", ".join(part.strip() for part in parts if part and part.strip())


class AddressCreate(BaseModel):
    city_id: int
    name: str | None = None
    spot: Point | None = None
    parsed: AddressFields | None = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def _ensure_name(self) -> "AddressCreate":
        if not (self.name and self.name.strip()) and self.parsed:
            self.name = self.parsed.compose_name()
        if not (self.name and self.name.strip()):
            raise ValueError("either name or parsed address fields are required")
        return self


class AddressRead(AddressCreate, UUIDMixin):
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


class AddressPatchData(PatchModel):
    name: str | None = None
    city_id: int | None = None
    spot: Point | None = None
    parsed: AddressFields | None = None


class AddressPatch(AddressPatchData, UUIDMixin): ...


class AddressPutData(AddressCreate): ...


class AddressPut(AddressPutData, UUIDMixin): ...


class AddressCascadeCreate(AddressFields):
    city: CityCascadeCreate
    spot: Point | None = None

