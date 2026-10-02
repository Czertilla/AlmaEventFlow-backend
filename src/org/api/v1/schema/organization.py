from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from core.schema.v1.mixin.model import PatchModelV1, UUIDMixinV1
from org.dto.organization import (
    OrganizationCreateDTO,
    OrganizationPatchDTO,
    OrganizationPutDTO,
)


class OrganizationBase(BaseModel):
    type: str
    name: str = Field(max_length=128)
    acronym: str | None = Field(max_length=16, default=None)
    principal_id: UUID | None = None
    address_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)


class OrganizationCreate(OrganizationBase, ToDTOMixinV1):
    __dto_cls__ = OrganizationCreateDTO


class OrganizationPreview(BaseModel, UUIDMixinV1):
    type: str
    name: str = Field(max_length=128)
    acronym: str | None = Field(max_length=16, default=None)


class OrganizationRead(FromDTOMixinV1, OrganizationBase, UUIDMixinV1): ...


class OrganizationPatchData(OrganizationBase, PatchModelV1):
    type: str | None = None
    name: str | None = Field(max_length=128, default=None)
    acronym: str | None = Field(max_length=16, default=None)


class OrganizationPatch(OrganizationPatchData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = OrganizationPatchDTO


class OrganizationPutData(OrganizationBase): ...


class OrganizationPut(OrganizationPutData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = OrganizationPutDTO
