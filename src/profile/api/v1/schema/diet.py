from profile.dto.diet import DietCreateDTO, DietPatchDTO, DietPutDTO

from pydantic import BaseModel, ConfigDict, Field

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from core.schema.v1.mixin.model import IDMixinV1, PatchModelV1


class DietCreate(BaseModel, ToDTOMixinV1):
    __dto_cls__ = DietCreateDTO

    name: str = Field(max_length=128)
    description: str | None = Field(max_length=512, default=None)

    model_config = ConfigDict(from_attributes=True)


class DietRead(FromDTOMixinV1, DietCreate, IDMixinV1): ...


class DietPatchData(PatchModelV1):
    name: str | None = Field(max_length=128, default=None)
    description: str | None = Field(max_length=512, default=None)


class DietPatch(DietPatchData, IDMixinV1, ToDTOMixinV1):
    __dto_cls__ = DietPatchDTO


class DietPutData(DietCreate): ...


class DietPut(DietPutData, IDMixinV1, ToDTOMixinV1):
    __dto_cls__ = DietPutDTO
