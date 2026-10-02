from pydantic import BaseModel, ConfigDict

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from geo.dto.city import CityCascadeCreateDTO


class CityCreate(BaseModel):
    name: str


class CityCascadeCreate(BaseModel, ToDTOMixinV1):
    __dto_cls__ = CityCascadeCreateDTO

    name: str
    region: str
    country: str


class CityRead(BaseModel, FromDTOMixinV1):
    id: int
    region_id: int
    name: str
    acronym: str | None = None

    model_config = ConfigDict(from_attributes=True)
