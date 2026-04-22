from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from datetime import date

from core.utils.mixin.pydantic import PatchModel, PutUUIDMixin, UUIDMixin


class NameVariantCreate(BaseModel):
    name: str = Field(max_length=128)
    surname: str = Field(max_length=128)
    patronymic: str | None = Field(max_length=128, default=None)

    model_config = ConfigDict(from_attributes=True)


class NameVariantRead(NameVariantCreate, UUIDMixin): ...


class NameVariantPatchData(PatchModel):
    name: str | None = Field(max_length=128, default=None)
    surname: str | None = Field(max_length=128, default=None)
    patronymic: str | None = Field(max_length=128, default=None)


class NameVariantPatch(NameVariantPatchData, UUIDMixin): ...


class NameVariantPutData(NameVariantCreate): ...


class NameVariantPut(NameVariantPutData, UUIDMixin): ...


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


class PassportItemRead(BaseModel, UUIDMixin):
    model_config = ConfigDict(from_attributes=True)


class PassportRead(PassportItemRead, PassportItemCreate):
    profile_id: UUID


class PassportPatchData(PatchModel):
    number: str | None = Field(max_length=32, default=None)
    name_variant: NameVariantPatchData | None = None
    expire_date: date | None = Field(default=None)
    is_foreign: bool | None = Field(default=None)
    issued_date: date | None = None
    issued_authority: str | None = None


class PassportPatch(PassportPatchData, UUIDMixin): ...


class PassportPutData(PassportItemCreate):
    profile_id: UUID


class PassportPut(PassportPutData, PutUUIDMixin): ...
