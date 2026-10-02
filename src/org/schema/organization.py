from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.schema.v1.mixin.model import PatchModelV1, UUIDMixinV1


class OrganizationCreate(BaseModel):
    type: str
    name: str = Field(max_length=128)
    acronym: str | None = Field(max_length=16, default=None)
    principal_id: UUID | None = None
    address_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class OrganizationPreview(BaseModel, UUIDMixinV1):
    type: str
    name: str = Field(max_length=128)
    acronym: str | None = Field(max_length=16, default=None)


class OrganizationRead(OrganizationCreate, UUIDMixinV1): ...


class OrganizationPatchData(OrganizationCreate, PatchModelV1):
    type: str | None = None
    name: str | None = Field(max_length=128, default=None)
    acronym: str | None = Field(max_length=16, default=None)


class OrganizationPatch(OrganizationPatchData, UUIDMixinV1): ...


class OrganizationPutData(OrganizationCreate): ...


class OrganizationPut(OrganizationPutData, UUIDMixinV1): ...
