from pydantic import BaseModel, ConfigDict, Field

from core.utils.mixin.pydantic import IDMixin, PatchModel


class DietCreate(BaseModel):
    name: str = Field(max_length=128)
    description: str | None = Field(max_length=512, default=None)

    model_config = ConfigDict(from_attributes=True)


class DietRead(DietCreate, IDMixin): ...


class DietPatchData(PatchModel):
    name: str | None = Field(max_length=128, default=None)
    description: str | None = Field(max_length=512, default=None)


class DietPatch(DietPatchData, IDMixin): ...


class DietPutData(DietCreate): ...


class DietPut(DietPutData, IDMixin): ...