from pydantic import BaseModel, ConfigDict, Field

from core.schema.v1.mixin.model import PatchModelV1, UUIDMixinV1


class PersonCreate(BaseModel):
    surname: str = Field(max_length=128)
    name: str = Field(max_length=128)
    patronymic: str | None = Field(max_length=128, default=None)

    model_config = ConfigDict(from_attributes=True)


class PersonItemRead(PersonCreate, UUIDMixinV1):
    patronymic: str | None = Field(max_length=128)


class PersonRead(PersonItemRead): ...


class PersonPatchData(PersonCreate, PatchModelV1):
    surname: str | None = Field(max_length=128, default=None)
    name: str | None = Field(max_length=128, default=None)


class PersonPatch(PersonPatchData, UUIDMixinV1): ...


class PersonPutData(PersonCreate):
    patronymic: str | None = Field(max_length=128, default=None)


class PersonPut(PersonPutData, UUIDMixinV1): ...
