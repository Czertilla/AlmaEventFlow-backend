from dataclasses import dataclass

from pydantic import BaseModel

from core.schema.v1.mixin.dto import ToDTOMixinV1


@dataclass(frozen=True)
class PointDTO:
    lat: float
    lon: float


@dataclass(frozen=True)
class PlaceDTO:
    name: str
    spot: PointDTO | None = None
    stops: list[PointDTO] | None = None
    tags: dict[str, str] | None = None


class Point(BaseModel, ToDTOMixinV1):
    __dto_cls__ = PointDTO

    lat: float
    lon: float


class Tags(BaseModel):
    kind: str


class Place(BaseModel, ToDTOMixinV1):
    __dto_cls__ = PlaceDTO

    name: str
    spot: Point | None = None
    stops: list[Point] | None = None
    tags: Tags | None = None


def test_nested_schemas_become_nested_dtos():
    place = Place(
        name="Gate",
        spot=Point(lat=1, lon=2),
        stops=[Point(lat=3, lon=4)],
    )

    dto = place.to_dto()

    assert dto.spot == PointDTO(lat=1, lon=2)
    assert dto.stops == [PointDTO(lat=3, lon=4)]


def test_a_nested_model_without_a_dto_stays_a_dict():
    dto = Place(name="Gate", tags=Tags(kind="park")).to_dto()

    assert dto.tags == {"kind": "park"}
    assert dto.spot is None
