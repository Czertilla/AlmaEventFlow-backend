from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from core.utils.mixin.pydantic import PatchModel, UUIDMixin


class FacultyCreate(BaseModel):
    name: str = Field(max_length=128)
    acronym: str | None = Field(max_length=16, default=None)
    principal_id: UUID | None = None
    address_id: UUID | None = None
    university_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class FacultyRead(FacultyCreate, UUIDMixin):
    type: str = Field(default="faculty", repr=False)


class FacultyPatchData(FacultyCreate, PatchModel):
    name: str | None = Field(max_length=128, default=None)
    acronym: str | None = Field(max_length=16, default=None)
    university_id: UUID | None = None


class FacultyPatch(FacultyPatchData, UUIDMixin): ...


class FacultyPutData(FacultyCreate): ...


class FacultyPut(FacultyPutData, UUIDMixin): ...
