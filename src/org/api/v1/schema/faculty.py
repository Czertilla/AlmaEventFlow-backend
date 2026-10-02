from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from core.schema.v1.mixin.model import PatchModelV1, UUIDMixinV1
from org.dto.faculty import (
    FacultyCreateDTO,
    FacultyPatchDTO,
    FacultyPutDTO,
)


class FacultyBase(BaseModel):
    name: str = Field(max_length=128)
    acronym: str | None = Field(max_length=16, default=None)
    principal_id: UUID | None = None
    address_id: UUID | None = None
    university_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class FacultyCreate(FacultyBase, ToDTOMixinV1):
    __dto_cls__ = FacultyCreateDTO


class FacultyRead(FromDTOMixinV1, FacultyBase, UUIDMixinV1):
    type: str = Field(default="faculty", repr=False)


class FacultyPatchData(FacultyBase, PatchModelV1):
    name: str | None = Field(max_length=128, default=None)
    acronym: str | None = Field(max_length=16, default=None)
    university_id: UUID | None = None


class FacultyPatch(FacultyPatchData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = FacultyPatchDTO


class FacultyPutData(FacultyBase): ...


class FacultyPut(FacultyPutData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = FacultyPutDTO
