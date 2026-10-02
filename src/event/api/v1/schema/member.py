from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from core.schema.v1.mixin.model import PatchModelV1, UUIDMixinV1
from event.api.v1.schema.role import RolePreview
from event.dto.member import (
    MemberCreateDataDTO,
    MemberCreateDTO,
    MemberPatchDTO,
    MemberPatchRolesDTO,
    MemberPutDTO,
)


class MemberCreateData(BaseModel, ToDTOMixinV1):
    __dto_cls__ = MemberCreateDataDTO

    person_id: UUID
    roles: list[UUID] = Field(max_length=25, default=[])
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class MemberCreate(MemberCreateData, ToDTOMixinV1):
    __dto_cls__ = MemberCreateDTO

    collective_id: UUID


class MemberRead(FromDTOMixinV1, MemberCreate, UUIDMixinV1):
    roles: list[RolePreview]


class MemberPatchData(PatchModelV1, ToDTOMixinV1):
    __dto_cls__ = MemberPatchRolesDTO

    roles: list[UUID] | None = Field(max_length=25, default=None)
    is_active: bool | None = None


class MemberPatch(MemberPatchData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = MemberPatchDTO


class MemberPutData(BaseModel):
    roles: list[UUID] = Field(max_length=25, default=[])
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class MemberPut(MemberPutData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = MemberPutDTO
