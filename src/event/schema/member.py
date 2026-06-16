from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from core.utils.mixin.pydantic import PatchModel, UUIDMixin
from event.schema.role import RolePreview


class MemberCreateData(BaseModel):
    person_id: UUID
    roles: list[UUID] = Field(max_length=25, default=[])
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class MemberCreate(MemberCreateData):
    collective_id: UUID


class MemberRead(MemberCreate, UUIDMixin):
    roles: list[RolePreview]


class MemberPatchData(PatchModel):
    roles: list[UUID] | None = Field(max_length=25, default=None)
    is_active: bool | None = None


class MemberPatch(MemberPatchData, UUIDMixin): ...


class MemberPutData(BaseModel):
    roles: list[UUID] = Field(max_length=25, default=[])
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class MemberPut(MemberPutData, UUIDMixin): ...
