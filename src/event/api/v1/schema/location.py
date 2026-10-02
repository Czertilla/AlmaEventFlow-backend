from pydantic import BaseModel, ConfigDict

from core.schema.v1.mixin.model import PatchModelV1, UUIDMixinV1


class LocationCreate(BaseModel):
    name: str

    model_config = ConfigDict(from_attributes=True)


class LocationRead(LocationCreate, UUIDMixinV1): ...


class LocationPatchData(PatchModelV1):
    name: str | None = None


class LocationPatch(LocationPatchData, UUIDMixinV1): ...


class LocationPutData(LocationCreate): ...


class LocationPut(LocationPutData, UUIDMixinV1): ...
