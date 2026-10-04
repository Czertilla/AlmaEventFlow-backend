from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from core.schema.v1.mixin.model import PatchModelV1, TimestampMixinV1, UUIDMixinV1
from geo.api.v1.schema.address import AddressRead
from geo.api.v1.schema.point import Point
from geo.dto.location import LocationCreateDTO, LocationPatchDTO, LocationPutDTO


def _check_address_or_spot(
    address_id: UUID | None, spot: object, name: str | None
) -> None:
    if address_id is None and spot is None:
        raise ValueError("a location needs at least one of address_id or spot")
    if address_id is not None and spot is not None and name is None:
        raise ValueError(
            "a location combining an address with its own spot needs a name "
            "to distinguish it from the plain address-proxy location"
        )


def _blank_to_none(value: str | None) -> str | None:
    return value.strip() or None if value else None


class LocationFields(BaseModel):
    name: str | None = Field(max_length=512, default=None)
    address_id: UUID | None = None
    spot: Point | None = None

    model_config = ConfigDict(from_attributes=True)


class LocationBase(LocationFields):
    _normalize_name = field_validator("name")(_blank_to_none)

    @model_validator(mode="after")
    def _validate_anchor(self) -> "LocationBase":
        _check_address_or_spot(self.address_id, self.spot, self.name)
        return self


class LocationCreate(LocationBase, ToDTOMixinV1):
    __dto_cls__ = LocationCreateDTO


class LocationRead(FromDTOMixinV1, LocationFields, UUIDMixinV1, TimestampMixinV1):
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

    @computed_field
    @property
    def display_name(self) -> str | None:
        """``name`` is ``None`` for an address-proxy location by design --
        this is the text other services should actually show/sync (matches
        the ``name || address?.name`` fallback already used across the
        frontend, e.g. ``useGeoSearch.ts``)."""
        return self.name or (self.address.name if self.address else None)


class LocationPatchData(PatchModelV1):
    name: str | None = Field(max_length=512, default=None)
    address_id: UUID | None = None
    spot: Point | None = None

    _normalize_name = field_validator("name")(_blank_to_none)


class LocationPatch(LocationPatchData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = LocationPatchDTO


class LocationPutData(LocationBase): ...


class LocationPut(LocationPutData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = LocationPutDTO


class LocationFromAddressCreate(BaseModel):
    """The "user picked an address, may or may not have bothered naming a
    location" flow -- ``name=None`` resolves to the (idempotent)
    address-proxy location instead of creating a new named one."""

    address_id: UUID
    name: str | None = Field(max_length=512, default=None)

    _normalize_name = field_validator("name")(_blank_to_none)
