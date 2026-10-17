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
from core.schema.v1.mixin.model import TimestampMixinV1, UUIDMixinV1
from geo.api.v1.schema.location import blank_to_none, check_address_or_spot
from geo.api.v1.schema.point import Point
from geo.api.v2.schema.address import AddressReadV2
from geo.dto.location import LocationCreateDTO


class LocationCreateV2(ToDTOMixinV1, BaseModel):
    """Anchor the location to an address or a point, or give only a `name`:
    then it is an address written as plain text, for a place nothing is known
    about."""

    __dto_cls__ = LocationCreateDTO

    name: str | None = Field(max_length=512, default=None)
    address_id: UUID | None = None
    spot: Point | None = None

    _normalize_name = field_validator("name")(blank_to_none)

    @model_validator(mode="after")
    def _validate_anchor(self) -> "LocationCreateV2":
        if self.address_id is None and self.spot is None:
            if self.name is None:
                raise ValueError("a location needs a name, an address_id or a spot")
            return self
        check_address_or_spot(self.address_id, self.spot, self.name)
        return self


class LocationReadV2(FromDTOMixinV1, BaseModel, UUIDMixinV1, TimestampMixinV1):
    name: str | None = None
    address_id: UUID | None = None
    spot: Point | None = None
    address: AddressReadV2 | None = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def display_name(self) -> str | None:
        return self.name or (self.address.name if self.address else None)

    @computed_field
    @property
    def locality(self) -> str | None:
        return self.address.locality if self.address else None

    @computed_field
    @property
    def map_uri(self) -> str | None:
        point = self.spot or (self.address.spot if self.address else None)
        if point is None:
            return None
        return f"geo:{point.lat},{point.lon}"
