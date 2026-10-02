from pydantic import BaseModel, ConfigDict, Field

from core.schema.v1.mixin.model import PatchModelV1, UUIDMixinV1


class OrganizationCreate(BaseModel):
    name: str = Field(max_length=128)
    acronym: str | None = Field(max_length=16, default=None)

    model_config = ConfigDict(from_attributes=True)


class OrganizationRead(OrganizationCreate, UUIDMixinV1): ...


class OrganizationPatchData(PatchModelV1):
    name: str | None = Field(max_length=128, default=None)
    acronym: str | None = Field(max_length=16, default=None)


class OrganizationPatch(OrganizationPatchData, UUIDMixinV1): ...


class OrganizationPutData(OrganizationCreate): ...


class OrganizationPut(OrganizationPutData, UUIDMixinV1): ...