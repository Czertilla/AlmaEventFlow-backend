from pydantic import BaseModel, ConfigDict, Field

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from geo.dto.point import PointDTO


class Point(BaseModel, FromDTOMixinV1, ToDTOMixinV1):
    __dto_cls__ = PointDTO

    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)

    model_config = ConfigDict(from_attributes=True)
