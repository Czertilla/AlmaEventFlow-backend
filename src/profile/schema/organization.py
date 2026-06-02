from pydantic import BaseModel, ConfigDict, Field

from core.utils.mixin.pydantic import PatchModel, UUIDMixin


class OrganizationCreate(BaseModel):
    name: str = Field(max_length=128)
    acronym: str | None = Field(max_length=16, default=None)

    model_config = ConfigDict(from_attributes=True)


class OrganizationRead(OrganizationCreate, UUIDMixin): ...


class OrganizationPatchData(PatchModel):
    name: str | None = Field(max_length=128, default=None)
    acronym: str | None = Field(max_length=16, default=None)


class OrganizationPatch(OrganizationPatchData, UUIDMixin): ...


class OrganizationPutData(OrganizationCreate): ...


class OrganizationPut(OrganizationPutData, UUIDMixin): ...