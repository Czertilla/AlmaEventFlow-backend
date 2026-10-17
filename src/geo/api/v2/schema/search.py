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
    state: Literal[
        "skipped", "ok", "cached", "timeout", "error", "unavailable", "throttled"
    ] = Field(
        description=(
            "`skipped`: the local answer was enough, or the request opted out. "
            "`ok` / `cached`: the external geocoder was asked. `timeout`, "
            "`error`, `unavailable`: it could not be, the answer is local only. "
            "`throttled`: the request budget towards the geocoder is spent, or it "
            "asked to slow down; the answer is local only."
        )
    )
    provider: str | None = None

    model_config = ConfigDict(from_attributes=True)


class Place(BaseModel):
    name: str
    region: str = Field(description="Region or state; empty when unknown.")
    country: str
    lat: float
    lon: float
    bbox: tuple[float, float, float, float] | None = Field(
        default=None,
        description="West, south, east, north: what a map fits to show the place.",
    )

    model_config = ConfigDict(from_attributes=True)


class SearchResponse(BaseModel, FromDTOMixinV1):
    items: list[SearchHit]
    external: ExternalStatus
    place: Place | None = Field(
        default=None,
        description=(
            "The settlement the text names, when it is one: the addresses listed are "
            "the nearest to its centre, and a map can move there."
        ),
    )

    model_config = ConfigDict(from_attributes=True)
