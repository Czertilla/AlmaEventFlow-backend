from profile.dto.person import PersonCreateDTO, PersonPatchDTO, PersonPutDTO

from pydantic import BaseModel, ConfigDict, Field

from core.database.sqlalchemy.mixins.models import TimestampMixin
from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from core.schema.v1.mixin.model import PatchModelV1, UUIDMixinV1


class PersonBase(BaseModel):
    surname: str = Field(max_length=128)
    name: str = Field(max_length=128)
    patronymic: str | None = Field(max_length=128, default=None)

    model_config = ConfigDict(from_attributes=True)


class PersonCreate(PersonBase, ToDTOMixinV1):
    __dto_cls__ = PersonCreateDTO


class PersonItemRead(FromDTOMixinV1, PersonBase, UUIDMixinV1):
    patronymic: str | None = Field(max_length=128)


class PersonRead(PersonItemRead, TimestampMixin): ...


class PersonPatchData(PersonBase, PatchModelV1):
    surname: str | None = Field(max_length=128, default=None)
    name: str | None = Field(max_length=128, default=None)


class PersonPatch(PersonPatchData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = PersonPatchDTO


class PersonPutData(PersonBase):
    patronymic: str | None = Field(max_length=128, default=None)


class PersonPut(PersonPutData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = PersonPutDTO
