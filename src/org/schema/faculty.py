from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.schema.v1.mixin.model import PatchModelV1, UUIDMixinV1


class FacultyCreate(BaseModel):
    name: str = Field(max_length=128)
    acronym: str | None = Field(max_length=16, default=None)
    principal_id: UUID | None = None
    address_id: UUID | None = None
    university_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class FacultyRead(FacultyCreate, UUIDMixinV1):
    type: str = Field(default="faculty", repr=False)


class FacultyPatchData(FacultyCreate, PatchModelV1):
    name: str | None = Field(max_length=128, default=None)
    acronym: str | None = Field(max_length=16, default=None)
    university_id: UUID | None = None


class FacultyPatch(FacultyPatchData, UUIDMixinV1): ...


class FacultyPutData(FacultyCreate): ...


class FacultyPut(FacultyPutData, UUIDMixinV1): ...
