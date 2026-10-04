from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from core.schema.v1.mixin.model import PatchModelV1, TimestampMixinV1, UUIDMixinV1
from org.dto.university import (
    UniversityCreateDTO,
    UniversityPatchDTO,
    UniversityPutDTO,
)


class UniversityBase(BaseModel):
    name: str = Field(max_length=128)
    acronym: str | None = Field(max_length=16, default=None)
    principal_id: UUID | None = None
    address_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class UniversityCreate(UniversityBase, ToDTOMixinV1):
    __dto_cls__ = UniversityCreateDTO


class UniversityRead(FromDTOMixinV1, UniversityBase, UUIDMixinV1, TimestampMixinV1):
    type: str = Field(default="university", repr=False)


class UniversityPatchData(UniversityBase, PatchModelV1):
    name: str | None = Field(max_length=128, default=None)
    acronym: str | None = Field(max_length=16, default=None)


class UniversityPatch(UniversityPatchData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = UniversityPatchDTO


class UniversityPutData(UniversityBase): ...


class UniversityPut(UniversityPutData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = UniversityPutDTO
