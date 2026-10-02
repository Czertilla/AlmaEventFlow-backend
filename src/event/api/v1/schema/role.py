from uuid import UUID

from pydantic import BaseModel, ConfigDict

from core.schema.v1.mixin.dto import FromDTOMixinV1, ToDTOMixinV1
from core.schema.v1.mixin.model import PatchModelV1, UUIDMixinV1
from event.dto.role import RoleCreateDTO, RolePatchDTO, RolePutDTO


class RoleCreateData(BaseModel):
    name: str

    model_config = ConfigDict(from_attributes=True)


class RoleCreate(RoleCreateData, ToDTOMixinV1):
    __dto_cls__ = RoleCreateDTO

    collective_id: UUID


class RolePreview(FromDTOMixinV1, RoleCreateData, UUIDMixinV1):
    model_config = ConfigDict(from_attributes=True, extra="ignore")


class RoleRead(FromDTOMixinV1, RoleCreate, UUIDMixinV1): ...


class RolePatchData(PatchModelV1):
    name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class RolePatch(RolePatchData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = RolePatchDTO


class RolePutData(RoleCreateData): ...


class RolePut(RolePutData, UUIDMixinV1, ToDTOMixinV1):
    __dto_cls__ = RolePutDTO
