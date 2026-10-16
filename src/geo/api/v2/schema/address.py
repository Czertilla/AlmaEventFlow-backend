from pydantic import BaseModel, ConfigDict, Field, computed_field

from core.schema.v1.mixin.dto import FromDTOMixinV1
from core.schema.v1.mixin.model import TimestampMixinV1, UUIDMixinV1
from geo.api.v1.schema.address import AddressFields
from geo.api.v1.schema.point import Point


class AddressReadV2(FromDTOMixinV1, BaseModel, UUIDMixinV1, TimestampMixinV1):
    city_id: int
    name: str = Field(description="The address itself: street, house, ...")
    locality: str = Field(
        description=(
            "City, and region and country when they add something, as one "
            'string: "Москва, Россия".'
        )
    )
    spot: Point | None = None
    parsed: AddressFields | None = None
    source: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def full_name(self) -> str:
        return f"{self.name}, {self.locality}" if self.locality else self.name

    @computed_field
    @property
    def map_uri(self) -> str | None:
        """RFC 5870 ``geo:`` URI."""
        if self.spot is None:
            return None
        return f"geo:{self.spot.lat},{self.spot.lon}"
