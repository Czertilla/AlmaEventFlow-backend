from pydantic import BaseModel, ConfigDict

from core.utils.mixin.pydantic import PatchModel, UUIDMixin


class LocationCreate(BaseModel):
    name: str

    model_config = ConfigDict(from_attributes=True)


class LocationRead(LocationCreate, UUIDMixin): ...


class LocationPatchData(PatchModel):
    name: str | None = None


class LocationPatch(LocationPatchData, UUIDMixin): ...


class LocationPutData(LocationCreate): ...


class LocationPut(LocationPutData, UUIDMixin): ...
