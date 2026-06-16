from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from core.utils.mixin.pydantic import PatchModel, UUIDMixin


class UniversityCreate(BaseModel):
    name: str = Field(max_length=128)
    acronym: str | None = Field(max_length=16, default=None)
    principal_id: UUID | None = None
    address_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class UniversityRead(UniversityCreate, UUIDMixin):
    type: str = Field(default="university", repr=False)


class UniversityPatchData(UniversityCreate, PatchModel):
    name: str | None = Field(max_length=128, default=None)
    acronym: str | None = Field(max_length=16, default=None)


class UniversityPatch(UniversityPatchData, UUIDMixin): ...


class UniversityPutData(UniversityCreate): ...


class UniversityPut(UniversityPutData, UUIDMixin): ...
