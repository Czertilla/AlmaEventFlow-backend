from pydantic import BaseModel, ConfigDict, Field
from core.utils.mixin.pydantic import PatchModel, UUIDMixin


class PersonCreate(BaseModel):
    name: str = Field(max_length=128)
    surname: str = Field(max_length=128)
    patronymic: str | None = Field(max_length=128, default=None)

    model_config = ConfigDict(from_attributes=True)


class PersonItemRead(PersonCreate, UUIDMixin):
    patronymic: str | None = Field(max_length=128)


class PersonRead(PersonItemRead): ...


class PersonPatchData(PersonCreate, PatchModel):
    name: str | None = Field(max_length=128, default=None)
    surname: str | None = Field(max_length=128, default=None)


class PersonPatch(PersonPatchData, UUIDMixin): ...


class PersonPutData(PersonCreate):
    patronymic: str | None = Field(max_length=128, default=None)


class PersonPut(PersonPutData, UUIDMixin): ...
