from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.schema.v1.mixin.model import PatchModelV1, UUIDMixinV1


class UniversityCreate(BaseModel):
    name: str = Field(max_length=128)
    acronym: str | None = Field(max_length=16, default=None)
    principal_id: UUID | None = None
    address_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class UniversityRead(UniversityCreate, UUIDMixinV1):
    type: str = Field(default="university", repr=False)


class UniversityPatchData(UniversityCreate, PatchModelV1):
    name: str | None = Field(max_length=128, default=None)
    acronym: str | None = Field(max_length=16, default=None)


class UniversityPatch(UniversityPatchData, UUIDMixinV1): ...


class UniversityPutData(UniversityCreate): ...


class UniversityPut(UniversityPutData, UUIDMixinV1): ...
