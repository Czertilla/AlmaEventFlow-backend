from pydantic import BaseModel, ConfigDict, Field

from core.utils.mixin.pydantic import PatchModel, IDMixin


class OrganizationCreate(BaseModel):
    name: str = Field(max_length=128)
    acronym: str | None = Field(max_length=16, default=None)

    model_config = ConfigDict(from_attributes=True)


class OrganizationRead(OrganizationCreate, IDMixin): ...


class OrganizationPatchData(PatchModel):
    name: str | None = Field(max_length=128, default=None)
    acronym: str | None = Field(max_length=16, default=None)


class OrganizationPatch(OrganizationPatchData, IDMixin): ...


class OrganizationPutData(OrganizationCreate): ...


class OrganizationPut(OrganizationPutData, IDMixin): ...