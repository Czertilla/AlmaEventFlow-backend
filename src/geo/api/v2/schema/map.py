from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from core.schema.v1.mixin.dto import FromDTOMixinV1
from geo.dto.map import MapClusterDTO, MapViewDTO


class PointGeometry(BaseModel):
    type: Literal["Point"] = "Point"
    coordinates: tuple[float, float] = Field(
        description="[longitude, latitude], the RFC 7946 order."
    )


class KindCounts(BaseModel):
    address: int
    location: int


class EntityProperties(BaseModel):
    cluster: Literal[False] = False
    kind: Literal["address", "location"]
    name: str
    locality: str


class ClusterProperties(BaseModel):
    cluster: Literal[True] = True
    point_count: int
    counts: KindCounts
    bbox: tuple[float, float, float, float] = Field(
        description=(
            "[west, south, east, north] of the clustered places; fit the map "
            "to it to open the cluster."
        )
    )


class EntityFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    id: UUID
    geometry: PointGeometry
    properties: EntityProperties


class ClusterFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    geometry: PointGeometry
    properties: ClusterProperties


class MapResponse(FromDTOMixinV1, BaseModel):
    """RFC 7946 FeatureCollection; `number_matched` and `number_returned`
    follow OGC API - Features."""

    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[EntityFeature | ClusterFeature]
    number_matched: int = Field(description="Places in the window, clustered or not.")
    number_returned: int = Field(description="Features in this response.")
    truncated: bool = Field(
        description="More features than `limit` were left out, smallest clusters first."
    )

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def _from_view(cls, data: Any) -> Any:
        if not isinstance(data, MapViewDTO):
            return data
        features: list[dict[str, Any]] = []
        for item in data.features:
            if isinstance(item, MapClusterDTO):
                features.append(
                    {
                        "geometry": {"coordinates": (item.lon, item.lat)},
                        "properties": {
                            "cluster": True,
                            "point_count": item.count,
                            "counts": {
                                "address": item.addresses,
                                "location": item.locations,
                            },
                            "bbox": (item.west, item.south, item.east, item.north),
                        },
                    }
                )
            else:
                features.append(
                    {
                        "id": item.id,
                        "geometry": {"coordinates": (item.lon, item.lat)},
                        "properties": {
                            "kind": item.kind,
                            "name": item.name,
                            "locality": item.locality,
                        },
                    }
                )
        return {
            "features": features,
            "number_matched": data.matched,
            "number_returned": len(features),
            "truncated": data.truncated,
        }
