from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from core.utils.mixin.pydantic import PatchModel, UUIDMixin
from geo.schema.point import Point


class LocationCreate(BaseModel):
    name: str = Field(max_length=512)
    address_id: UUID | None
    spot: Point

    model_config = ConfigDict(from_attributes=True)


class LocationRead(LocationCreate, UUIDMixin): ...


class LocationPatchData(PatchModel):
    name: str | None = Field(max_length=512, default=None)
    address_id: UUID | None = None
    spot: Point | None = None


class LocationPatch(LocationPatchData, UUIDMixin): ...


class LocationPutData(LocationCreate): ...


class LocationPut(LocationPutData, UUIDMixin): ...
