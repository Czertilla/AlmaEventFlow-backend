from uuid import UUID

from pydantic import BaseModel, ConfigDict, computed_field

from core.schema.v1.mixin.dto import FromDTOMixinV1
from core.schema.v1.mixin.model import TimestampMixinV1, UUIDMixinV1
from geo.api.v1.schema.point import Point
from geo.api.v2.schema.address import AddressReadV2


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
