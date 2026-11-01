from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.schema.v1.mixin.dto import FromDTOMixinV1


class PersonNamesData(BaseModel):
    ids: list[UUID] = Field(max_length=200)


class PersonNameRead(FromDTOMixinV1, BaseModel):
    id: UUID
    surname: str | None
    name: str | None
    patronymic: str | None

    model_config = ConfigDict(from_attributes=True)


class PersonNamesRead(BaseModel):
    items: list[PersonNameRead]
