from datetime import date
from profile.dto.passport import (
    NameVariantCreateDTO,
    NameVariantPatchDataDTO,
    NameVariantPatchDTO,
    NameVariantPutDTO,
    PassportCreateDTO,
    PassportPatchDTO,
    PassportPutDTO,
)
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from core.schema.v1.mixin.model import (
    PatchModelV1,
    PutUUIDMixinV1,
    TimestampMixinV1,
    UUIDMixinV1,
)


class NameVariantCreate(BaseModel, ToDTOMixinV1):
    __dto_cls__ = NameVariantCreateDTO

    surname: str = Field(max_length=128)
    name: str = Field(max_length=128)
    patronymic: str | None = Field(max_length=128, default=None)

    model_config = ConfigDict(from_attributes=True)


class NameVariantRead(FromDTOMixinV1, NameVariantCreate, UUIDMixinV1): ...


class NameVariantPatchData(PatchModelV1, ToDTOMixinV1):
    __dto_cls__ = NameVariantPatchDataDTO

    surname: str | None = Field(max_length=128, default=None)
    name: str | None = Field(max_length=128, default=None)
    patronymic: str | None = Field(max_length=128, default=None)


class NameVariantPatch(NameVariantPatchData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = NameVariantPatchDTO


class NameVariantPutData(NameVariantCreate): ...


class NameVariantPut(NameVariantPutData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = NameVariantPutDTO


class PassportItemBase(BaseModel):
    number: str = Field(max_length=32)
    expire_date: date
    is_foreign: bool

    model_config = ConfigDict(from_attributes=True)


class PassportItemCreate(PassportItemBase):
    issued_date: date | None = None
    issued_authority: str | None = None
    name_variant: NameVariantCreate | None = None

    model_config = ConfigDict(from_attributes=True)


class PassportCreate(PassportItemCreate, ToDTOMixinV1):
    __dto_cls__ = PassportCreateDTO

    profile_id: UUID


class PassportItemRead(FromDTOMixinV1, PassportItemBase, UUIDMixinV1): ...


class PassportRead(PassportItemRead, PassportItemCreate, TimestampMixinV1):
    profile_id: UUID


class PassportPatchData(PatchModelV1):
    number: str | None = Field(max_length=32, default=None)
    name_variant: NameVariantPatchData | None = None
    expire_date: date | None = Field(default=None)
    is_foreign: bool | None = Field(default=None)
    issued_date: date | None = None
    issued_authority: str | None = None


class PassportPatch(PassportPatchData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = PassportPatchDTO


class PassportPutData(PassportItemCreate):
    profile_id: UUID


class PassportPut(PassportPutData, PutUUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = PassportPutDTO
