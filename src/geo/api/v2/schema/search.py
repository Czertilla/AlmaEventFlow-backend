from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from core.schema.v1.mixin.dto import FromDTOMixinV1
from geo.api.v2.schema.address import AddressReadV2
from geo.api.v2.schema.location import LocationReadV2

Origin = Literal["local", "external"]


class AddressHit(BaseModel):
    kind: Literal["address"]
    origin: Origin
    score: float | None = Field(
        description="Relevance, higher is better; null when ranked by distance only."
    )
    address: AddressReadV2

    model_config = ConfigDict(from_attributes=True)


class LocationHit(BaseModel):
    kind: Literal["location"]
    origin: Origin
    score: float | None = Field(
        description="Relevance, higher is better; null when ranked by distance only."
    )
    location: LocationReadV2

    model_config = ConfigDict(from_attributes=True)


SearchHit = Annotated[AddressHit | LocationHit, Field(discriminator="kind")]


class ExternalStatus(BaseModel, FromDTOMixinV1):
    state: Literal["skipped", "ok", "cached", "timeout", "error", "unavailable"] = (
        Field(
            description=(
                "`skipped`: the local answer was enough, or the request opted out. "
                "`ok` / `cached`: the external geocoder was asked. `timeout`, "
                "`error`, `unavailable`: it could not be, the answer is local only."
            )
        )
    )
    provider: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SearchResponse(BaseModel, FromDTOMixinV1):
    items: list[SearchHit]
    external: ExternalStatus

    model_config = ConfigDict(from_attributes=True)
