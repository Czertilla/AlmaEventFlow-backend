from pydantic import BaseModel, ConfigDict, Field

from core.schema.v1.mixin.model import IDMixinV1, PatchModelV1


class DietCreate(BaseModel):
    name: str = Field(max_length=128)
    description: str | None = Field(max_length=512, default=None)

    model_config = ConfigDict(from_attributes=True)


class DietRead(DietCreate, IDMixinV1): ...


class DietPatchData(PatchModelV1):
    name: str | None = Field(max_length=128, default=None)
    description: str | None = Field(max_length=512, default=None)


class DietPatch(DietPatchData, IDMixinV1): ...


class DietPutData(DietCreate): ...


class DietPut(DietPutData, IDMixinV1): ...