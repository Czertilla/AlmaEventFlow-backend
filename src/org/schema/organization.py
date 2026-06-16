from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from core.utils.mixin.pydantic import PatchModel, UUIDMixin


class OrganizationCreate(BaseModel):
    type: str
    name: str = Field(max_length=128)
    acronym: str | None = Field(max_length=16, default=None)
    principal_id: UUID | None = None
    address_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class OrganizationPreview(BaseModel, UUIDMixin):
    type: str
    name: str = Field(max_length=128)
    acronym: str | None = Field(max_length=16, default=None)


class OrganizationRead(OrganizationCreate, UUIDMixin): ...


class OrganizationPatchData(OrganizationCreate, PatchModel):
    type: str | None = None
    name: str | None = Field(max_length=128, default=None)
    acronym: str | None = Field(max_length=16, default=None)


class OrganizationPatch(OrganizationPatchData, UUIDMixin): ...


class OrganizationPutData(OrganizationCreate): ...


class OrganizationPut(OrganizationPutData, UUIDMixin): ...
