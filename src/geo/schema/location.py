from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from core.utils.mixin.pydantic import PatchModel, UUIDMixin
from geo.schema.address import AddressRead
from geo.schema.point import Point


def _check_address_xor_spot(address_id: UUID | None, spot: object) -> None:
    if (address_id is not None) == (spot is not None):
        raise ValueError(
            "a location must have exactly one of address_id or spot, not "
            "both and not neither"
        )


class LocationCreate(BaseModel):
    name: str | None = Field(max_length=512, default=None)
    address_id: UUID | None = None
    spot: Point | None = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def _validate_anchor(self) -> "LocationCreate":
        _check_address_xor_spot(self.address_id, self.spot)
        return self


class LocationRead(LocationCreate, UUIDMixin):
    address: AddressRead | None = None
    """Populated when the repository eager-loads the relationship (see
    ``LocationService.read``/``search``) -- lets ``map_uri`` below resolve
    for an address-anchored location, which has no ``spot`` of its own."""

    @computed_field
    @property
    def map_uri(self) -> str | None:
        point = self.spot or (self.address.spot if self.address else None)
        if point is None:
            return None
        return f"geo:{point.lat},{point.lon}"


class LocationPatchData(PatchModel):
    name: str | None = Field(max_length=512, default=None)
    address_id: UUID | None = None
    spot: Point | None = None


class LocationPatch(LocationPatchData, UUIDMixin): ...


class LocationPutData(LocationCreate): ...


class LocationPut(LocationPutData, UUIDMixin): ...


class LocationFromAddressCreate(BaseModel):
    """The "user picked an address, may or may not have bothered naming a
    location" flow -- ``name=None`` resolves to the (idempotent)
    address-proxy location instead of creating a new named one."""

    address_id: UUID
    name: str | None = Field(max_length=512, default=None)
