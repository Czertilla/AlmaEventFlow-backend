from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.schema.v1.mixin.model import PatchModelV1, PutUUIDMixinV1, UUIDMixinV1


class NameVariantCreate(BaseModel):
    surname: str = Field(max_length=128)
    name: str = Field(max_length=128)
    patronymic: str | None = Field(max_length=128, default=None)

    model_config = ConfigDict(from_attributes=True)


class NameVariantRead(NameVariantCreate, UUIDMixinV1): ...


class NameVariantPatchData(PatchModelV1):
    surname: str | None = Field(max_length=128, default=None)
    name: str | None = Field(max_length=128, default=None)
    patronymic: str | None = Field(max_length=128, default=None)


class NameVariantPatch(NameVariantPatchData, UUIDMixinV1): ...


class NameVariantPutData(NameVariantCreate): ...


class NameVariantPut(NameVariantPutData, UUIDMixinV1): ...


class PassportItemCreate(BaseModel):
    number: str = Field(max_length=32)
    expire_date: date
    is_foreign: bool
    issued_date: date | None = None
    issued_authority: str | None = None
    name_variant: NameVariantCreate | None = None

    model_config = ConfigDict(from_attributes=True)


class PassportCreate(PassportItemCreate):
    profile_id: UUID


class PassportItemRead(BaseModel, UUIDMixinV1):
    model_config = ConfigDict(from_attributes=True)


class PassportRead(PassportItemRead, PassportItemCreate):
    profile_id: UUID


class PassportPatchData(PatchModelV1):
    number: str | None = Field(max_length=32, default=None)
    name_variant: NameVariantPatchData | None = None
    expire_date: date | None = Field(default=None)
    is_foreign: bool | None = Field(default=None)
    issued_date: date | None = None
    issued_authority: str | None = None


class PassportPatch(PassportPatchData, UUIDMixinV1): ...


class PassportPutData(PassportItemCreate):
    profile_id: UUID


class PassportPut(PassportPutData, PutUUIDMixinV1): ...
